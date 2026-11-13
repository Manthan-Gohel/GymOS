from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


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


def get_payments_provider() -> PaymentsProvider:
    provider = os.getenv("PAYMENTS_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockPaymentsProvider()
    # Real Razorpay/UPI requires credentials (BLK-002); never fake.
    raise NotImplementedError(f"Payments provider '{provider}' not implemented; use mock or add credentials")
