from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


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


def get_llm_provider() -> LLMProvider:
    enabled = os.getenv("LLM_ENABLED", "false").lower() in {"1", "true", "yes"}
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if not enabled:
        return CannedFallbackLLMProvider()
    if provider == "mock":
        return MockLLMProvider()
    # Real LLM requires credentials (BLK-004); never fake.
    return CannedFallbackLLMProvider()
