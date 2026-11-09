"""Runs AnthropicLLM against a fake HTTP server that speaks the Messages streaming protocol."""
import json

import httpx2 as httpx
import pytest

from app.ai.llm import AnthropicLLM, LLMError


def sse(events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def stream_body():
    plan_json = json.dumps({"title": "T", "summary": "S", "components": [{"id": "c1"}, {"id": "c2"}]})
    chunks = [plan_json[i:i + 15] for i in range(0, len(plan_json), 15)]
    return sse([
        {"type": "message_start", "message": {"id": "m1", "type": "message", "role": "assistant", "model": "claude-x", "content": [],
                                              "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 0}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Planning "}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "it."}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "tu1", "name": "propose_plan", "input": {}}},
        *({"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": c}} for c in chunks),
        {"type": "content_block_stop", "index": 1},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None}, "usage": {"output_tokens": 50}},
        {"type": "message_stop"},
    ])


def make_llm(handler):
    llm = AnthropicLLM("sk-ant-test", "claude-x")
    llm.client = llm.client.with_options(http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0)
    return llm


def test_stream_translates_events_and_sends_cache_control():
    sent = {}

    def handler(request):
        sent["body"] = json.loads(request.content)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=stream_body())

    tools = [{"name": "a", "input_schema": {"type": "object"}}, {"name": "propose_plan", "input_schema": {"type": "object"}}]
    evs = list(make_llm(handler).stream("SYSTEM", "CTX", [{"role": "user", "content": "hi"}], tools))
    assert "".join(e["delta"] for e in evs if e["kind"] == "text") == "Planning it."
    assert any(e["kind"] == "tool_start" and e["name"] == "propose_plan" for e in evs)
    snaps = [e["snapshot"] for e in evs if e["kind"] == "tool_input"]
    assert snaps and all(e["name"] == "propose_plan" for e in evs if e["kind"] == "tool_input")
    assert snaps[-1] == {"title": "T", "summary": "S", "components": [{"id": "c1"}, {"id": "c2"}]}
    final = evs[-1]
    assert final["kind"] == "message" and final["stop_reason"] == "tool_use"
    assert final["content"] == [{"type": "text", "text": "Planning it."},
                                {"type": "tool_use", "id": "tu1", "name": "propose_plan", "input": {"title": "T", "summary": "S", "components": [{"id": "c1"}, {"id": "c2"}]}}]
    body = sent["body"]
    assert body["system"][0] == {"type": "text", "text": "SYSTEM", "cache_control": {"type": "ephemeral"}}
    assert body["system"][1] == {"type": "text", "text": "CTX"}
    assert body["tools"][-1]["cache_control"] == {"type": "ephemeral"} and "cache_control" not in body["tools"][0]
    assert body["stream"] is True and body["model"] == "claude-x"


@pytest.mark.parametrize("status,needle", [(401, "rejected the API key"), (404, "wasn't found"), (429, "rate-limiting"), (529, "overloaded")])
def test_errors_become_friendly(status, needle):
    def handler(request):
        return httpx.Response(status, json={"type": "error", "error": {"type": "x", "message": "boom"}})
    with pytest.raises(LLMError, match=needle):
        list(make_llm(handler).stream("S", "", [{"role": "user", "content": "hi"}], []))
