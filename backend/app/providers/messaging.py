from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol


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


def get_messaging_provider() -> MessagingProvider:
    provider = os.getenv("MESSAGING_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockMessagingProvider()
    # Real WhatsApp provider requires credentials (BLK-001); never fake.
    raise NotImplementedError(f"Messaging provider '{provider}' not implemented; use mock or add credentials")
