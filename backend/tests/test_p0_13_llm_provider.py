from unittest.mock import MagicMock, patch

from app.providers.llm import (
    CannedFallbackLLMProvider,
    MockLLMProvider,
    RealLLMProvider,
    get_llm_provider,
)


def test_mock_llm_provider_returns_reply():
    provider = MockLLMProvider()
    resp = provider.generate_reply(prompt="What are timings?", context={"timings": "6am-10pm"})
    assert resp["ok"] is True
    assert "reply" in resp


def test_canned_fallback_indicates_handoff():
    provider = CannedFallbackLLMProvider()
    resp = provider.generate_reply(prompt="Anything", context={})
    assert resp["ok"] is False
    assert resp["handoff"] is True
    assert "reply" in resp


def test_get_llm_provider_falls_back_when_disabled(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_ENABLED", "false")
    provider = get_llm_provider()
    assert isinstance(provider, CannedFallbackLLMProvider)


def test_get_llm_provider_real(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_ENABLED", "true")
    provider = get_llm_provider()
    assert isinstance(provider, RealLLMProvider)


def test_real_llm_provider_calls_completion_endpoint():
    provider = RealLLMProvider(api_key="sk-test-key", model="gpt-4o-mini")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "We are open from 6:00 AM to 10:00 PM."}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = provider.generate_reply(prompt="What are timings?", context={"timings": "6 AM - 10 PM"})
        assert res["ok"] is True
        assert res["provider"] == "real-llm"
        assert res["reply"] == "We are open from 6:00 AM to 10:00 PM."
        mock_post.assert_called_once()
