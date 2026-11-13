from unittest.mock import MagicMock, patch

from app.providers.messaging import (
    MockMessagingProvider,
    OpenWAMessagingProvider,
    get_messaging_provider,
)


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


def test_get_messaging_provider_openwa(monkeypatch):
    monkeypatch.setenv("MESSAGING_PROVIDER", "openwa")
    provider = get_messaging_provider()
    assert isinstance(provider, OpenWAMessagingProvider)


def test_openwa_messaging_provider_sends_message_via_http():
    provider = OpenWAMessagingProvider(base_url="http://mock-openwa:8080", api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"success": True, "msgId": "WA_123"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = provider.send_message(to="9876543210", body="Hello from GymOS!")
        assert res["status"] == "sent"
        assert res["provider"] == "openwa"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["chatId"] == "919876543210@c.us"
        assert kwargs["json"]["content"] == "Hello from GymOS!"
