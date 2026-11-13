from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import settings


class LLMProvider(Protocol):
    def generate_reply(self, *, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]: ...


@dataclass
class MockLLMProvider:
    """Mock LLM for dev/tests. Chatbot-only usage."""

    def generate_reply(self, *, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        return {
            "ok": True,
            "handoff": False,
            "reply": f"[mock-llm] grounded reply for: {prompt[:80]}",
            "context_keys": sorted(ctx.keys()),
            "provider": "mock",
        }


@dataclass
class CannedFallbackLLMProvider:
    """Explicit fallback: canned reply + human handoff when LLM unavailable/disabled."""

    def generate_reply(self, *, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        _ = prompt, context
        return {
            "ok": False,
            "handoff": True,
            "reply": "Thanks for your message. A staff member will get back to you shortly.",
            "provider": "canned-fallback",
        }


@dataclass
class RealLLMProvider:
    """Live LLM provider communicating with OpenAI/Gemini/OpenRouter/Groq compatible API."""

    api_key: str = field(default_factory=lambda: settings.llm_api_key or os.getenv("LLM_API_KEY", ""))
    model: str = field(default_factory=lambda: settings.llm_model or os.getenv("LLM_MODEL", "gpt-4o-mini"))
    base_url: str = field(default_factory=lambda: (settings.llm_base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/"))
    timeout_seconds: float = 15.0

    def generate_reply(self, *, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = context or {}
        context_str = "\n".join(f"- {k}: {v}" for k, v in ctx.items()) if ctx else "No additional context."

        system_prompt = (
            "You are the official WhatsApp assistant for GymOS gym operations. "
            "STRICT GROUNDING RULES:\n"
            "1. Answer ONLY based on the provided gym information below (timings, plans, trainers, location).\n"
            "2. If asked about medical advice, injuries, pain, rehabilitation, refunds, complaints, or legal matters, "
            "do NOT advise. Explicitly state that a staff member will review and assist.\n"
            "3. NEVER invent or hallucinate prices, discounts, or promises not in the context.\n"
            "4. Keep replies concise, polite, and suitable for WhatsApp (1-3 sentences max).\n\n"
            f"Gym Context:\n{context_str}"
        )

        # Ollama and other local servers need no Authorization header
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 200,
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

            handoff = any(
                w in content.lower()
                for w in ["staff member", "human", "reception", "doctor", "physio", "refund", "complaint"]
            )
            return {
                "ok": True,
                "handoff": handoff,
                "reply": content,
                "provider": "real-llm",
                "model": self.model,
            }
        except Exception as e:
            # Automatic graceful fallback to canned reply + handoff on network or API error
            fallback = CannedFallbackLLMProvider().generate_reply(prompt=prompt, context=context)
            fallback["error"] = str(e)
            return fallback


def get_llm_provider() -> LLMProvider:
    enabled = os.getenv("LLM_ENABLED", str(settings.llm_enabled)).lower() in {"1", "true", "yes"}
    provider = os.getenv("LLM_PROVIDER", settings.llm_provider).lower()

    if not enabled:
        return CannedFallbackLLMProvider()
    if provider == "mock":
        return MockLLMProvider()
    if provider in {"real", "openai", "gemini", "groq", "openrouter", "deepseek", "ollama"}:
        return RealLLMProvider()

    return CannedFallbackLLMProvider()
