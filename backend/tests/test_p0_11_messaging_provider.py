from app.providers.messaging import MockMessagingProvider, get_messaging_provider


def test_mock_messaging_provider_stores_sent_message_with_audit_payload():
    provider = MockMessagingProvider()
    result = provider.send_template(
        to="+919999999999",
        template_name="welcome",
        params={"name": "Test"},
        who="reception:1",
        what="welcome_message",
        why="new_member",
    )
    assert result["status"] == "sent"
    assert len(provider.sent_messages) == 1
    msg = provider.sent_messages[0]
    assert msg["to"] == "+919999999999"
    assert msg["template_name"] == "welcome"
    assert msg["who"] == "reception:1"
    assert msg["what"] == "welcome_message"
    assert msg["why"] == "new_member"


def test_get_messaging_provider_defaults_to_mock(monkeypatch):
    monkeypatch.setenv("MESSAGING_PROVIDER", "mock")
    provider = get_messaging_provider()
    assert isinstance(provider, MockMessagingProvider)
