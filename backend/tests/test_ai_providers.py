"""Any AI provider, model limits and AI usage (26 Oct 2026)."""
import json

import httpx
import pytest

from app.ai import usage
from app.ai.llm import LLMError, OpenAICompatLLM, partial_json, to_openai_messages
from app.ai.providers import model_catalog, resolve
from app.routers import chats
from app.services import ai_provider

from .test_chat import ScriptedLLM, events, send, text_turn


# ---------- providers ----------

def test_provider_names_resolve():
    assert resolve("Claude", None).kind == "anthropic"
    g = resolve("google", None)
    assert g.key == "gemini" and g.kind == "openai" and g.base_url.startswith("https://generativelanguage.googleapis.com")
    assert resolve("OpenAI", None).base_url == "https://api.openai.com/v1"
    assert resolve("azure openai", "https://x.openai.azure.com/openai/v1/").auth == "api-key"
    custom = resolve("Acme LLM", None)
    assert custom.key == "custom" and custom.label == "Acme LLM" and custom.base_url == ""
    assert resolve("Acme LLM", "https://llm.acme.com/v1/").base_url == "https://llm.acme.com/v1"


def test_model_catalog_prefix_match():
    assert model_catalog("claude-sonnet-4-20250514")["input"] == 3.0
    assert model_catalog("gpt-4o-mini-2024-07-18")["output"] == 0.6  # longest prefix wins over gpt-4o
    assert model_catalog("anthropic/claude-sonnet-4.5")["matched"] == "claude-sonnet-4-5"
    assert model_catalog("my-own-model") is None


def test_partial_json_reads_a_streaming_object():
    assert partial_json('{"title": "A", "components": [{"id": "c1"}, {"id": "c2", "lab') == {"title": "A", "components": [{"id": "c1"}, {"id": "c2"}]}
    assert partial_json('{"summary": "half a sent') == {"summary": "half a sent"}
    assert partial_json("not json") is None


# ---------- OpenAI-compatible adapter ----------

def sse(*chunks):
    return "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"


def test_openai_compatible_stream_text_tools_and_usage():
    sent = []

    def handler(request: httpx.Request):
        sent.append(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer key-123"
        body = sse(
            {"choices": [{"delta": {"content": "Reading "}}]},
            {"choices": [{"delta": {"content": "the org"}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "get_org_schema", "arguments": '{"objec'}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'ts": ["Account"]}'}}]}, "finish_reason": "tool_calls"}]},
            {"choices": [], "usage": {"prompt_tokens": 1200, "completion_tokens": 40, "prompt_tokens_details": {"cached_tokens": 1000}}},
        )
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    llm = OpenAICompatLLM("key-123", "gpt-4o", "https://api.openai.com/v1", transport=httpx.MockTransport(handler))
    history = [{"role": "user", "content": "Add a field"},
               {"role": "assistant", "content": [{"type": "text", "text": "Checking"}, {"type": "tool_use", "id": "t0", "name": "search_org_metadata", "input": {"q": "x"}}]},
               {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t0", "content": "none found"}]}]
    evs = list(llm.stream("SYSTEM", "CONTEXT", history, [{"name": "get_org_schema", "description": "d", "input_schema": {"type": "object"}}], max_tokens=5000))
    body = sent[0]
    assert body["model"] == "gpt-4o" and body["stream"] is True and body["max_completion_tokens"] == 5000  # OpenAI's own API
    assert body["messages"][0] == {"role": "system", "content": "SYSTEM\n\nCONTEXT"}
    assert body["messages"][2]["tool_calls"][0]["function"] == {"name": "search_org_metadata", "arguments": '{"q": "x"}'}
    assert body["messages"][3] == {"role": "tool", "tool_call_id": "t0", "content": "none found"}
    assert body["tools"][0]["function"]["name"] == "get_org_schema"
    assert "".join(e["delta"] for e in evs if e["kind"] == "text") == "Reading the org"
    final = evs[-1]
    assert final["kind"] == "message" and final["stop_reason"] == "tool_use"
    assert final["content"][1] == {"type": "tool_use", "id": "call_1", "name": "get_org_schema", "input": {"objects": ["Account"]}}
    assert final["usage"] == {"input": 200, "output": 40, "cache_read": 1000, "cache_write": 0}


def test_openai_compatible_retries_with_settings_the_provider_accepts():
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        if "stream_options" in body:
            return httpx.Response(400, json={"error": {"message": "Unknown parameter: stream_options"}})
        if body["max_tokens"] > 8192:
            return httpx.Response(400, json={"error": {"message": "max_tokens is too large: 32000. This model supports at most 8192 completion tokens"}})
        return httpx.Response(200, text=sse({"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}))

    llm = OpenAICompatLLM("k", "llama", "https://api.groq.com/openai/v1", transport=httpx.MockTransport(handler))
    evs = list(llm.stream("s", "", [{"role": "user", "content": "hi"}], [], max_tokens=32000))
    assert evs[-1]["content"] == [{"type": "text", "text": "ok"}] and evs[-1]["stop_reason"] == "end_turn"
    assert len(seen) == 3 and seen[-1]["max_tokens"] == 8192 and "stream_options" not in seen[-1]


def test_openai_compatible_errors_are_plain():
    llm = OpenAICompatLLM("k", "nope", "https://api.x.ai/v1", transport=httpx.MockTransport(lambda r: httpx.Response(404, json={"error": {"message": "model not found"}})))
    with pytest.raises(LLMError, match="wasn't found"):
        list(llm.stream("s", "", [{"role": "user", "content": "hi"}], []))


def test_azure_uses_api_key_header():
    def handler(request):
        assert request.headers["api-key"] == "az-key" and "authorization" not in request.headers
        return httpx.Response(200, text=sse({"choices": [{"delta": {"content": "hi"}, "finish_reason": "stop"}]}))
    llm = OpenAICompatLLM("az-key", "my-deployment", "https://r.openai.azure.com/openai/v1", auth="api-key", transport=httpx.MockTransport(handler))
    assert list(llm.stream("s", "", [{"role": "user", "content": "x"}], []))[-1]["content"][0]["text"] == "hi"


def test_messages_translation_keeps_errors_visible():
    out = to_openai_messages("S", "", [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "boom", "is_error": True}]}])
    assert out[1] == {"role": "tool", "tool_call_id": "a", "content": "ERROR: boom"}


# ---------- verify: limits from the provider ----------

def test_verify_openai_compatible_reads_rate_limits_and_model_limits():
    def handler(request):
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(200, json={"choices": [{"message": {"content": "p"}}]},
                                  headers={"x-ratelimit-limit-requests": "500", "x-ratelimit-limit-tokens": "30000"})
        return httpx.Response(200, json={"id": "gpt-4o", "context_window": 128000})
    r = ai_provider._verify_openai("OpenAI", "k", "gpt-4o", "https://api.openai.com/v1", "bearer", transport=httpx.MockTransport(handler))
    assert r.ok and r.limits == {"requests_per_minute": 500, "tokens_per_minute": 30000}
    assert r.model_info["context"] == 128000 and r.model_info["max_output"] == 16384 and r.model_info["source"] == "provider"


def test_verify_openai_compatible_bad_key():
    r = ai_provider._verify_openai("Groq", "bad", "m", "https://api.groq.com/openai/v1", "bearer",
                                   transport=httpx.MockTransport(lambda req: httpx.Response(401, json={"error": {"message": "Invalid API Key"}})))
    assert not r.ok and "rejected the API key" in r.message


def test_rate_limit_headers_anthropic():
    assert ai_provider.rate_limits({"anthropic-ratelimit-requests-limit": "50", "anthropic-ratelimit-input-tokens-limit": "30000",
                                    "anthropic-ratelimit-output-tokens-limit": "8000"}) == {
        "requests_per_minute": 50, "input_tokens_per_minute": 30000, "output_tokens_per_minute": 8000}


# ---------- settings: any provider ----------

def test_save_any_provider(client, auth, monkeypatch):
    seen = []
    monkeypatch.setattr(ai_provider, "verify", lambda p, k, m, b=None: seen.append((p, k, m, b)) or ai_provider.VerifyResult(True, "Connected."))
    r = client.put("/api/settings/ai-provider", json={"provider": "Acme LLM", "model": "acme-1", "api_key": "k-1"}, headers=auth)
    assert r.status_code == 400 and "needs a base URL" in r.json()["detail"]
    r = client.put("/api/settings/ai-provider", json={"provider": "Acme LLM", "model": "acme-1", "api_key": "k-1",
                                                     "base_url": "https://llm.acme.com/v1/"}, headers=auth)
    out = r.json()
    assert r.status_code == 200 and seen[-1] == ("Acme LLM", "k-1", "acme-1", "https://llm.acme.com/v1")
    assert out["provider_name"] == "Acme LLM" and out["kind"] == "openai" and out["base_url"] == "https://llm.acme.com/v1"
    # a known name fills the address but is shown back as typed
    out = client.put("/api/settings/ai-provider", json={"provider": "Google", "model": "gemini-2.5-pro"}, headers=auth).json()
    assert out["provider"] == "gemini" and out["provider_name"] == "Google" and out["api_key_masked"].endswith("k-1"[-4:])
    r = client.put("/api/settings/ai-provider", json={"provider": "OpenAI", "model": "gpt-4o", "base_url": "ftp://x"}, headers=auth)
    assert r.status_code == 400 and "https://" in r.json()["detail"]


def test_credits_count_tokens():
    from app.ai.providers import credits_for
    assert credits_for({"input": 1500, "output": 500, "cache_read": 10_000, "cache_write": 0}) == 3.0


def test_make_llm_picks_the_adapter(client, auth, monkeypatch):
    from app.ai.llm import AnthropicLLM
    from app.models import AIProviderConfig
    from app.security import encrypt
    cfg = AIProviderConfig(provider="openai", model="gpt-4o", api_key_enc=encrypt("sk-1"), api_key_last4="sk-1")
    assert isinstance(chats.make_llm(cfg), OpenAICompatLLM)
    cfg.provider = "anthropic"
    assert isinstance(chats.make_llm(cfg), AnthropicLLM)


# ---------- usage in credits ----------

@pytest.fixture
def ready(client, auth, snow, monkeypatch):
    from .conftest import connect_instance
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    client.put("/api/settings/ai-provider", json={"provider": "anthropic", "model": "claude-sonnet-4-6", "api_key": "sk-ant-test-1234567890"}, headers=auth)
    connect_instance(client, auth)
    return auth


def with_usage(turn, inp, out, cache_read=0):
    turn[-1] = {**turn[-1], "usage": {"input": inp, "output": out, "cache_read": cache_read, "cache_write": 0}}
    return turn


def test_chat_calls_count_credits(client, ready, monkeypatch):
    llm = ScriptedLLM([with_usage(text_turn("Hi there"), 10_000, 2_000, cache_read=50_000), with_usage(text_turn("Again"), 1_000, 1_000)])
    monkeypatch.setattr(chats, "llm_factory", lambda cfg: llm)
    chat = client.post("/api/chats", headers=ready).json()
    assert events(send(client, ready, chat["id"], "hello"))[-1]["type"] == "done"
    send(client, ready, chat["id"], "again")
    u = client.get("/api/settings/ai-usage", headers=ready).json()
    # (10,000 + 2,000 + 50,000 × 0.1) / 1,000 = 17, then (1,000 + 1,000) / 1,000 = 2
    assert u["used"] == 19 and u["calls"] == 2 and "allowance" not in u
    assert u["model"] == "claude-sonnet-4-6" and u["provider"] == "anthropic"  # as typed and u["current"] is True
    assert u["by_operation"] == [{"key": "chat", "label": "Chat and planning", "credits": 19}]
    assert u["by_member"][0]["name"] == "Vasu Dharavath" and u["by_day"][-1]["credits"] == 19


def test_tagged_calls_count_as_their_operation(client, ready):
    from app.db import SessionLocal
    from app.models import AIProviderConfig, AIUsage
    db = SessionLocal()
    cfg = db.query(AIProviderConfig).first()
    base = ScriptedLLM([with_usage(text_turn("a"), 100, 10), with_usage(text_turn("b"), 100, 10)])
    m = usage.metered(base, cfg, user_id=None, operation="chat", chat_id="c1")
    list(usage.tag(m, "generate", "p1").stream("s", "", [], []))
    list(usage.tag(m, "auto_repair", "p1").stream("s", "", [], []))
    rows = db.query(AIUsage).order_by(AIUsage.created_at).all()
    assert [(r.operation, r.plan_id, r.chat_id, r.credits) for r in rows] == [("generate", "p1", "c1", 0.11), ("auto_repair", "p1", "c1", 0.11)]
    assert usage.tag(base, "fix") is base  # unmetered models pass through
    db.close()


def test_usage_months(client, ready):
    u = client.get("/api/settings/ai-usage?month=2026-01", headers=ready).json()
    assert u["month"] == "2026-01" and u["previous"] == "2025-12" and u["next"] == "2026-02" and u["used"] == 0 and u["current"] is False
    assert len(u["by_day"]) == 31


def test_platform_shows_ai_credits_this_month(client, ready, monkeypatch):
    llm = ScriptedLLM([with_usage(text_turn("x"), 1000, 100)])
    monkeypatch.setattr(chats, "llm_factory", lambda cfg: llm)
    chat = client.post("/api/chats", headers=ready).json()
    send(client, ready, chat["id"], "hello")
    from app.db import SessionLocal
    from app.models import Workspace
    from app.services import platform
    db = SessionLocal()
    row = platform.workspace_row(db, db.query(Workspace).first())
    assert row["ai_month"] == {"credits": 1, "calls": 1}
    db.close()
