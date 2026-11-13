from unittest.mock import MagicMock, patch

from app.providers.payments import (
    MockPaymentsProvider,
    YouPIPaymentsProvider,
    get_payments_provider,
)


def test_mock_payments_provider_records_payment_flow():
    provider = MockPaymentsProvider()
    created = provider.create_payment(amount=1500, currency="INR", method="upi", metadata={"member_id": 1})
    assert created["status"] == "created"
    assert created["amount"] == 1500
    recorded = provider.record_payment(payment_id=created["payment_id"], status="captured", reference="cash-001")
    assert recorded["status"] == "captured"
    assert len(provider.payments) == 1
    assert provider.payments[0]["reference"] == "cash-001"


def test_get_payments_provider_defaults_to_mock(monkeypatch):
    monkeypatch.setenv("PAYMENTS_PROVIDER", "mock")
    provider = get_payments_provider()
    assert isinstance(provider, MockPaymentsProvider)


def test_get_payments_provider_youpi(monkeypatch):
    monkeypatch.setenv("PAYMENTS_PROVIDER", "youpi")
    provider = get_payments_provider()
    assert isinstance(provider, YouPIPaymentsProvider)


def test_youpi_payments_provider_create_and_record():
    provider = YouPIPaymentsProvider(
        base_url="http://mock-youpi:3000",
        merchant_key="test-merchant",
        webhook_secret="test-secret",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "checkout_url": "http://mock-youpi:3000/pay/123",
        "upi_intent": "upi://pay?pa=test@upi",
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp):
        res = provider.create_payment(amount=2000, currency="INR", method="upi", metadata={"plan_id": 2})
        assert res["status"] == "created"
        assert res["provider"] == "youpi-pg"
        assert res["amount"] == 2000
        assert "checkout_url" in res

    recorded = provider.record_payment(payment_id=res["payment_id"], status="paid", reference="UTR998877")
    assert recorded["status"] == "paid"
    assert recorded["reference"] == "UTR998877"
