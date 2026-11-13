from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import settings


class PaymentsProvider(Protocol):
    def create_payment(
        self, *, amount: float | int, currency: str, method: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    def record_payment(
        self, *, payment_id: str, status: str, reference: str | None = None
    ) -> dict[str, Any]: ...


@dataclass
class MockPaymentsProvider:
    payments: list[dict[str, Any]] = field(default_factory=list)

    def create_payment(
        self, *, amount: float | int, currency: str, method: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payment = {
            "payment_id": str(uuid.uuid4()),
            "amount": amount,
            "currency": currency,
            "method": method,
            "status": "created",
            "metadata": metadata or {},
            "reference": None,
            "provider": "mock",
        }
        self.payments.append(payment)
        return dict(payment)

    def record_payment(self, *, payment_id: str, status: str, reference: str | None = None) -> dict[str, Any]:
        for p in self.payments:
            if p["payment_id"] == payment_id:
                p["status"] = status
                if reference is not None:
                    p["reference"] = reference
                return dict(p)
        raise KeyError(payment_id)


@dataclass
class YouPIPaymentsProvider:
    """Real payments provider integrating with self-hosted YouPI-PG (UPI Gateway)."""

    base_url: str = field(default_factory=lambda: settings.youpi_base_url.rstrip("/"))
    merchant_key: str = field(default_factory=lambda: settings.youpi_merchant_key)
    webhook_secret: str = field(default_factory=lambda: settings.youpi_webhook_secret)
    timeout_seconds: float = 10.0
    recorded_records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create_payment(
        self, *, amount: float | int, currency: str, method: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        order_id = f"YPI_{uuid.uuid4().hex[:12]}"
        meta = metadata or {}
        endpoint = f"{self.base_url}/api/orders"

        headers = {
            "Content-Type": "application/json",
            "X-Merchant-Key": self.merchant_key,
        }

        payload = {
            "order_id": order_id,
            "amount": float(amount),
            "currency": currency,
            "method": method,
            "metadata": meta,
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            # If YouPI instance is not reachable or in simulation, create local tracking object
            data = {
                "checkout_url": f"{self.base_url}/checkout/{order_id}",
                "upi_intent": f"upi://pay?pa=gym@upi&pn=GymOS&am={amount}&tr={order_id}",
            }

        record = {
            "payment_id": order_id,
            "amount": amount,
            "currency": currency,
            "method": method,
            "status": "created",
            "metadata": meta,
            "reference": None,
            "checkout_url": data.get("checkout_url"),
            "upi_intent": data.get("upi_intent"),
            "provider": "youpi-pg",
        }
        self.recorded_records[order_id] = record
        return record

    def record_payment(self, *, payment_id: str, status: str, reference: str | None = None) -> dict[str, Any]:
        record = self.recorded_records.get(payment_id)
        if record is None:
            record = {
                "payment_id": payment_id,
                "status": status,
                "reference": reference,
                "provider": "youpi-pg",
            }
            self.recorded_records[payment_id] = record
        else:
            record["status"] = status
            if reference is not None:
                record["reference"] = reference
        return dict(record)

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        if not self.webhook_secret:
            return False
        expected = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)


def get_payments_provider() -> PaymentsProvider:
    provider = os.getenv("PAYMENTS_PROVIDER", settings.payments_provider).lower()
    if provider == "mock":
        return MockPaymentsProvider()
    if provider in {"youpi", "youpi-pg", "youpipg"}:
        return YouPIPaymentsProvider()
    raise NotImplementedError(f"Payments provider '{provider}' not implemented; use 'mock' or 'youpi'")
