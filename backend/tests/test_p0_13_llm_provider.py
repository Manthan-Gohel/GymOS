from app.providers.llm import CannedFallbackLLMProvider, MockLLMProvider, get_llm_provider


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
