"""VULN/local-LLM: ollama provider selects RealLLMProvider and needs no API key."""
from unittest.mock import MagicMock, patch

from app.providers.llm import CannedFallbackLLMProvider, RealLLMProvider, get_llm_provider


def test_ollama_provider_selected_when_enabled(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_ENABLED", "true")
    provider = get_llm_provider()
    assert isinstance(provider, RealLLMProvider)


def test_disabled_llm_still_falls_back_to_canned(monkeypatch):
    monkeypatch.delenv("LLM_ENABLED", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    provider = get_llm_provider()
    assert isinstance(provider, CannedFallbackLLMProvider)


def test_ollama_request_omits_auth_header_and_uses_local_base_url():
    provider = RealLLMProvider(api_key="", model="llama3.1", base_url="http://localhost:11434/v1")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": "Open 6 AM to 10 PM."}}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = provider.generate_reply(prompt="Timings?", context={"timings": "6 AM - 10 PM"})

    assert res["ok"] is True
    assert res["reply"] == "Open 6 AM to 10 PM."
    headers = mock_post.call_args.kwargs["headers"]
    assert "Authorization" not in headers
    assert mock_post.call_args.args[0] == "http://localhost:11434/v1/chat/completions"


def test_llm_network_error_falls_back_to_canned_handoff():
    provider = RealLLMProvider(api_key="", model="llama3.1", base_url="http://localhost:11434/v1")
    with patch("httpx.Client.post", side_effect=ConnectionError("refused")):
        res = provider.generate_reply(prompt="Timings?", context={})
    assert res["ok"] is False
    assert res["handoff"] is True
    assert "reply" in res
