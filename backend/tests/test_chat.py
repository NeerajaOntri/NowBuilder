"""The workspace chat: streamed answers, attachments, history, rename and delete."""
import json

import pytest

from app.routers import chats
from app.services import ai_provider

from .conftest import connect_instance


class ScriptedLLM:
    """Plays back pre-written model turns (stream events) and records what it was sent."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = []

    def stream(self, system, context, messages, tools, max_tokens=16000):
        self.calls.append({"system": system, "context": context, "messages": json.loads(json.dumps(messages)), "tools": [t["name"] for t in tools]})
        yield from self.turns.pop(0)


def text_turn(text):
    words = text.split(" ")
    return [*({"kind": "text", "delta": w + (" " if i < len(words) - 1 else "")} for i, w in enumerate(words)),
            {"kind": "message", "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}]


def tool_turn(name, args, tid="t1", lead=""):
    evs = [{"kind": "text", "delta": lead}] if lead else []
    content = ([{"type": "text", "text": lead}] if lead else []) + [{"type": "tool_use", "id": tid, "name": name, "input": args}]
    evs.append({"kind": "message", "content": content, "stop_reason": "tool_use"})
    return evs


def events(resp):
    return [json.loads(line[6:]) for line in resp.text.split("\n\n") if line.startswith("data: ")]


def send(client, auth, chat_id, text, files=None):
    return client.post(f"/api/chats/{chat_id}/messages", data={"text": text}, files=files, headers=auth)


@pytest.fixture
def ready(client, auth, snow, monkeypatch):
    """User with a verified AI provider and a connected instance."""
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    client.put("/api/settings/ai-provider", json={"provider": "anthropic", "model": "claude-sonnet-5-5", "api_key": "sk-ant-test-1234567890"}, headers=auth)
    connect_instance(client, auth)
    return auth


def use_llm(monkeypatch, turns):
    llm = ScriptedLLM(turns)
    monkeypatch.setattr(chats, "llm_factory", lambda cfg: llm)
    return llm


def test_question_answered_with_servicenow_skills(client, ready, monkeypatch):
    llm = use_llm(monkeypatch, [text_turn("Use a before rule: it changes the record without another update.")])
    chat = client.post("/api/chats", headers=ready).json()
    r = send(client, ready, chat["id"], "Before vs after business rule for setting a field?")
    evs = events(r)
    assert r.headers["content-type"].startswith("text/event-stream")
    assert evs[0]["type"] == "start" and evs[-1]["type"] == "done"
    assert "".join(e["delta"] for e in evs if e["type"] == "text").startswith("Use a before rule")
    call = llm.calls[0]
    assert "Connected instance: Dev" in call["context"]
    assert call["tools"][0] == "propose_plan"  # the plan tool leads, so a build request can't miss it
    assert {"get_table_schema", "search_instance_artifacts", "get_instance_artifact"} <= set(call["tools"])
    assert '<skill name="servicenow-business-rules">' in call["system"] and '<skill name="servicenow-development-standards">' in call["system"]
    full = client.get(f"/api/chats/{chat['id']}", headers=ready).json()
    assert full["title"].startswith("Before vs after") and [m["role"] for m in full["messages"]] == ["user", "assistant"]


def test_history_goes_back_to_the_model(client, ready, monkeypatch):
    llm = use_llm(monkeypatch, [text_turn("First answer."), text_turn("Second answer.")])
    chat = client.post("/api/chats", headers=ready).json()
    send(client, ready, chat["id"], "first question")
    send(client, ready, chat["id"], "second question")
    assert [m["role"] for m in llm.calls[1]["messages"]] == ["user", "assistant", "user"]
    assert llm.calls[1]["messages"][1]["content"] == "First answer."


def test_attachment_text_goes_with_the_message(client, ready, monkeypatch):
    llm = use_llm(monkeypatch, [text_turn("Read it.")])
    chat = client.post("/api/chats", headers=ready).json()
    r = send(client, ready, chat["id"], "Build this", files=[("files", ("brd.txt", b"Incidents from VIPs get priority 1.", "text/plain"))])
    assert events(r)[-1]["type"] == "done"
    assert '<attached_document name="brd.txt">' in llm.calls[0]["messages"][0]["content"]


def test_tool_error_reaches_the_model_and_the_answer_still_arrives(client, ready, snow, monkeypatch):
    snow.forbidden.add("sys_db_object")
    llm = use_llm(monkeypatch, [tool_turn("get_table_schema", {"tables": ["incident"]}), text_turn("I couldn't read the table list.")])
    chat = client.post("/api/chats", headers=ready).json()
    evs = events(send(client, ready, chat["id"], "fields on incident?"))
    assert {"type": "status", "text": "Reading fields on incident"} in evs and evs[-1]["type"] == "done"
    result = llm.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "isn't allowed to read sys_db_object" in result["content"]


def test_no_ai_provider_is_a_plain_message(client, auth):
    chat = client.post("/api/chats", headers=auth).json()
    r = send(client, auth, chat["id"], "hi")
    assert r.status_code == 400 and "AI provider" in r.json()["detail"]


def test_rename_and_delete(client, ready):
    chat = client.post("/api/chats", headers=ready).json()
    assert client.patch(f"/api/chats/{chat['id']}", json={"title": "Priority rules"}, headers=ready).json()["title"] == "Priority rules"
    assert client.delete(f"/api/chats/{chat['id']}", headers=ready).status_code == 204
    assert client.get("/api/chats", headers=ready).json() == []
