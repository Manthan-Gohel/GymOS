from app.providers.payments import MockPaymentsProvider, get_payments_provider


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
