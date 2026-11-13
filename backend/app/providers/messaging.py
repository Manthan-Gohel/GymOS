from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import settings


class MessagingProvider(Protocol):
    def send_template(
        self,
        *,
        to: str,
        template_name: str,
        params: dict[str, Any] | None = None,
        who: str | None = None,
        what: str | None = None,
        why: str | None = None,
    ) -> dict[str, Any]: ...

    def send_message(
        self,
        *,
        to: str,
        body: str,
        who: str | None = None,
        what: str | None = None,
        why: str | None = None,
        template_name: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass
class MockMessagingProvider:
    sent_messages: list[dict[str, Any]] = field(default_factory=list)

    def _record(self, payload: dict[str, Any]) -> dict[str, Any]:
        msg = {"status": "sent", "provider": "mock", **payload}
        self.sent_messages.append(msg)
        return msg

    def send_template(
        self,
        *,
        to: str,
        template_name: str,
        params: dict[str, Any] | None = None,
        who: str | None = None,
        what: str | None = None,
        why: str | None = None,
    ) -> dict[str, Any]:
        return self._record(
            {
                "to": to,
                "template_name": template_name,
                "params": params or {},
                "who": who,
                "what": what,
                "why": why,
                "kind": "template",
            }
        )

    def send_message(
        self,
        *,
        to: str,
        body: str,
        who: str | None = None,
        what: str | None = None,
        why: str | None = None,
        template_name: str | None = None,
    ) -> dict[str, Any]:
        return self._record(
            {
                "to": to,
                "body": body,
                "template_name": template_name,
                "who": who,
                "what": what,
                "why": why,
                "kind": "message",
            }
        )


@dataclass
class OpenWAMessagingProvider:
    """Real WhatsApp provider integrating with openWA Easy API (wa-automate-nodejs)."""

    base_url: str = field(default_factory=lambda: settings.openwa_base_url.rstrip("/"))
    api_key: str = field(default_factory=lambda: settings.openwa_api_key)
    session_id: str = field(default_factory=lambda: settings.openwa_session_id)
    timeout_seconds: float = 10.0

    def _format_chat_id(self, phone: str) -> str:
        clean = re.sub(r"[^\d]", "", phone)
        # Default Indian 10-digit number to 91 country code
        if len(clean) == 10:
            clean = f"91{clean}"
        return f"{clean}@c.us"

    def send_message(
        self,
        *,
        to: str,
        body: str,
        who: str | None = None,
        what: str | None = None,
        why: str | None = None,
        template_name: str | None = None,
    ) -> dict[str, Any]:
        chat_id = self._format_chat_id(to)
        endpoint = f"{self.base_url}/sendText"

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api_key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "chatId": chat_id,
            "content": body,
            "sessionId": self.session_id,
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}

            return {
                "status": "sent",
                "provider": "openwa",
                "to": to,
                "body": body,
                "template_name": template_name,
                "who": who,
                "what": what,
                "why": why,
                "response": data,
            }
        except Exception as e:
            return {
                "status": "failed",
                "provider": "openwa",
                "to": to,
                "body": body,
                "template_name": template_name,
                "who": who,
                "what": what,
                "why": why,
                "error": str(e),
            }

    def send_template(
        self,
        *,
        to: str,
        template_name: str,
        params: dict[str, Any] | None = None,
        who: str | None = None,
        what: str | None = None,
        why: str | None = None,
    ) -> dict[str, Any]:
        p = params or {}
        # Controlled template rendering for business-initiated notifications
        if template_name == "welcome":
            body = f"Welcome to GymOS, {p.get('name', 'Member')}! Your fitness journey starts today. Reach out anytime with questions."
        elif template_name == "expiry_warning":
            body = f"Hi {p.get('name', 'Member')}, your gym membership expires in {p.get('days', 3)} days ({p.get('expiry_date', '')}). Renew soon to keep your streak!"
        elif template_name == "payment_due":
            body = f"Dear {p.get('name', 'Member')}, outstanding dues of Rs {p.get('amount', '0')} are pending for your gym membership. Please settle at reception or via UPI."
        else:
            # Fallback template formatting
            kv = ", ".join(f"{k}: {v}" for k, v in p.items())
            body = f"[{template_name.upper()}] Notice: {kv}"

        return self.send_message(
            to=to,
            body=body,
            who=who,
            what=what or f"template:{template_name}",
            why=why,
            template_name=template_name,
        )


def get_messaging_provider() -> MessagingProvider:
    provider = os.getenv("MESSAGING_PROVIDER", settings.messaging_provider).lower()
    if provider == "mock":
        return MockMessagingProvider()
    if provider in {"openwa", "wa-automate", "whatsapp"}:
        return OpenWAMessagingProvider()
    raise NotImplementedError(f"Messaging provider '{provider}' not implemented; use 'mock' or 'openwa'")
