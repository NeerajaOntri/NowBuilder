"""Model access behind a small interface, so the chat engine can be tested with a scripted model.

Events yielded by `LLM.stream`:
  {"kind": "text", "delta": str}
  {"kind": "tool_start", "index": int, "id": str, "name": str}
  {"kind": "tool_input", "index": int, "id": str, "name": str, "snapshot": dict}   # partial input so far
  {"kind": "message", "content": [block dicts], "stop_reason": str, "usage": {...}}   # always last

`usage` = {"input", "output", "cache_read", "cache_write"} tokens of that one model call (used by
`ai/usage.py` to count AI credits). Messages always use Anthropic's block format; the
OpenAI-compatible adapter translates both ways.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Protocol

import anthropic


class LLMError(Exception):
    """A model call failed; the message is safe to show to the user."""


class LLM(Protocol):
    def stream(self, system: str, context: str, messages: list[dict], tools: list[dict], max_tokens: int = 16000) -> Iterator[dict]: ...


class AnthropicLLM:
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        kw = {"base_url": base_url} if base_url and base_url.rstrip("/") != "https://api.anthropic.com" else {}
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=300, **kw)
        self.model = model

    def stream(self, system: str, context: str, messages: list[dict], tools: list[dict], max_tokens: int = 16000) -> Iterator[dict]:
        # The system prompt and tools are identical across turns: cache them. The context (org, plan) changes.
        system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        if context:
            system_blocks.append({"type": "text", "text": context})
        tools = [*tools[:-1], {**tools[-1], "cache_control": {"type": "ephemeral"}}] if tools else tools
        tool_blocks: dict[int, tuple[str, str]] = {}
        try:
            with self.client.messages.stream(model=self.model, max_tokens=max_tokens, system=system_blocks, messages=messages, tools=tools) as s:
                for ev in s:
                    if ev.type == "content_block_start" and ev.content_block.type == "tool_use":
                        tool_blocks[ev.index] = (ev.content_block.id, ev.content_block.name)
                        yield {"kind": "tool_start", "index": ev.index, "id": ev.content_block.id, "name": ev.content_block.name}
                    elif ev.type == "text":
                        yield {"kind": "text", "delta": ev.text}
                    elif ev.type == "input_json":
                        idx = len(s.current_message_snapshot.content) - 1
                        tid, name = tool_blocks.get(idx, ("", ""))
                        if isinstance(ev.snapshot, dict):
                            yield {"kind": "tool_input", "index": idx, "id": tid, "name": name, "snapshot": ev.snapshot}
                final = s.get_final_message()
        except anthropic.AuthenticationError as e:
            raise LLMError("Your AI provider rejected the API key. Update it in Settings → AI provider.") from e
        except anthropic.PermissionDeniedError as e:
            raise LLMError("Your API key doesn't have access to this model. Change the model in Settings → AI provider.") from e
        except anthropic.NotFoundError as e:
            raise LLMError(f"Model '{self.model}' wasn't found. Check the model name in Settings → AI provider.") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Your AI provider is rate-limiting requests. Wait a minute and try again.") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Couldn't reach the AI provider. Check your connection and try again.") from e
        except anthropic.APIStatusError as e:
            if e.status_code == 529 or "overloaded" in str(e).lower():
                raise LLMError("The AI provider is overloaded right now. Try again in a minute.") from e
            raise LLMError(f"The AI provider returned an error ({e.status_code}). Try again.") from e
        content: list[dict] = []
        for b in final.content:
            if b.type == "text":
                content.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                content.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        u = getattr(final, "usage", None)
        usage = {"input": getattr(u, "input_tokens", 0) or 0, "output": getattr(u, "output_tokens", 0) or 0,
                 "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0, "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0}
        yield {"kind": "message", "content": content, "stop_reason": final.stop_reason, "usage": usage}


# ---------- OpenAI-compatible providers (OpenAI, Gemini, Azure, Groq, DeepSeek, Mistral, OpenRouter, …) ----------

def to_openai_messages(system: str, context: str, messages: list[dict]) -> list[dict]:
    """Anthropic-style history → Chat Completions messages."""
    out: list[dict] = [{"role": "system", "content": system + (f"\n\n{context}" if context else "")}]
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            out.append({"role": m["role"], "content": c})
            continue
        if m["role"] == "assistant":
            text = "".join(b.get("text", "") for b in c if b["type"] == "text")
            calls = [{"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b["input"])}}
                     for b in c if b["type"] == "tool_use"]
            msg: dict = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
            continue
        for b in c:
            if b["type"] == "tool_result":
                body = b.get("content")
                if not isinstance(body, str):
                    body = json.dumps(body)
                out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": ("ERROR: " if b.get("is_error") else "") + body})
        texts = [b["text"] for b in c if b["type"] == "text"]
        if texts:
            out.append({"role": "user", "content": "\n\n".join(texts)})
    return out


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                              "parameters": t.get("input_schema") or {"type": "object", "properties": {}}}} for t in tools]


def partial_json(text: str) -> dict | None:
    """Best-effort parse of a JSON object that is still streaming in (for live plan drafts)."""
    stack: list[str] = []
    cuts: list[tuple[int, tuple]] = []  # places where the text can be cut and closed
    in_str = esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
            cuts.append((i + 1, tuple(stack)))
        elif ch in "}]":
            if stack:
                stack.pop()
            cuts.append((i + 1, tuple(stack)))
        elif ch == ",":
            cuts.append((i, tuple(stack)))
    candidates = []
    if not in_str:
        candidates.append(text + "".join(reversed(stack)))
    elif not esc:
        candidates.append(text + '"' + "".join(reversed(stack)))
    candidates += [text[:pos] + "".join(reversed(st)) for pos, st in reversed(cuts[-4:])]
    for cand in candidates:
        try:
            data = json.loads(cand)
        except ValueError:
            continue
        return data if isinstance(data, dict) else None
    return None


class OpenAICompatLLM:
    """Chat Completions with streaming and tool calls, over plain HTTP (httpx)."""

    def __init__(self, api_key: str, model: str, base_url: str, auth: str = "bearer", transport=None):
        self.api_key, self.model, self.base_url, self.auth = api_key, model, base_url.rstrip("/"), auth
        self.transport = transport  # tests pass an httpx.MockTransport
        self.max_param = "max_completion_tokens" if "api.openai.com" in self.base_url else "max_tokens"
        self.with_usage = True

    def headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.auth == "api-key":
            h["api-key"] = self.api_key
        else:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _client(self):
        import httpx
        return httpx.Client(timeout=httpx.Timeout(300, connect=30), transport=self.transport)

    def stream(self, system: str, context: str, messages: list[dict], tools: list[dict], max_tokens: int = 16000) -> Iterator[dict]:
        import httpx
        body: dict = {"model": self.model, "messages": to_openai_messages(system, context, messages), "stream": True}
        if tools:
            body["tools"] = to_openai_tools(tools)
        limit = max_tokens
        for _attempt in range(4):
            body.pop("max_tokens", None)
            body.pop("max_completion_tokens", None)
            body[self.max_param] = limit
            if self.with_usage:
                body["stream_options"] = {"include_usage": True}
            else:
                body.pop("stream_options", None)
            try:
                with self._client() as http, http.stream("POST", f"{self.base_url}/chat/completions", json=body, headers=self.headers()) as r:
                    if r.status_code >= 400:
                        text = r.read().decode(errors="replace")
                        retry = self._adjust(r.status_code, text, limit)
                        if retry is not None:
                            limit = retry
                            continue
                        raise _http_error(r.status_code, text, self.model)
                    yield from self._events(r)
                    return
            except httpx.HTTPError as e:
                raise LLMError("Couldn't reach the AI provider. Check the base URL and your connection, then try again.") from e
        raise LLMError("The AI provider kept refusing the request settings. Check the model name in Settings → AI provider.")

    def _adjust(self, status_code: int, text: str, limit: int) -> int | None:
        """Retry with settings the provider accepts (returns the new token limit), or None."""
        low = text.lower()
        if status_code != 400:
            return None
        if "stream_options" in low and self.with_usage:
            self.with_usage = False
            return limit
        if "max_completion_tokens" in low and self.max_param == "max_tokens" and "unsupported" in low:
            self.max_param = "max_completion_tokens"
            return limit
        if "max_tokens" in low and "unsupported" in low and self.max_param == "max_completion_tokens":
            self.max_param = "max_tokens"
            return limit
        if ("max_tokens" in low or "max_completion_tokens" in low or "maximum" in low) and re.search(r"\d{3,}", low):
            smaller = [int(n) for n in re.findall(r"\d{3,7}", low) if 0 < int(n) < limit]
            return max(smaller) if smaller else (limit // 2 if limit > 1024 else None)
        return None

    def _events(self, r) -> Iterator[dict]:
        text_parts: list[str] = []
        calls: dict[int, dict] = {}
        parsed_len: dict[int, int] = {}
        finish = None
        usage: dict = {}
        for line in r.iter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except ValueError:
                continue
            if chunk.get("error"):
                err = chunk["error"]
                raise LLMError(f"The AI provider returned an error: {err.get('message', err) if isinstance(err, dict) else err}")
            if chunk.get("usage"):
                u = chunk["usage"]
                cached = ((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
                usage = {"input": max(0, (u.get("prompt_tokens") or 0) - cached), "output": u.get("completion_tokens") or 0,
                         "cache_read": cached, "cache_write": 0}
            for ch in chunk.get("choices") or []:
                delta = ch.get("delta") or {}
                if delta.get("content"):
                    text_parts.append(delta["content"])
                    yield {"kind": "text", "delta": delta["content"]}
                for tc in delta.get("tool_calls") or []:
                    i = tc.get("index", 0)
                    call = calls.get(i)
                    fn = tc.get("function") or {}
                    if call is None:
                        call = calls[i] = {"id": tc.get("id") or f"call_{i}", "name": fn.get("name") or "", "args": ""}
                        yield {"kind": "tool_start", "index": i, "id": call["id"], "name": call["name"]}
                    elif fn.get("name") and not call["name"]:
                        call["name"] = fn["name"]
                    if fn.get("arguments"):
                        call["args"] += fn["arguments"]
                        if len(call["args"]) - parsed_len.get(i, 0) >= 400:
                            parsed_len[i] = len(call["args"])
                            snap = partial_json(call["args"])
                            if snap is not None:
                                yield {"kind": "tool_input", "index": i, "id": call["id"], "name": call["name"], "snapshot": snap}
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
        content: list[dict] = []
        text = "".join(text_parts)
        if text:
            content.append({"type": "text", "text": text})
        for i in sorted(calls):
            c = calls[i]
            try:
                args = json.loads(c["args"] or "{}")
            except ValueError:
                args = partial_json(c["args"]) or {}
            content.append({"type": "tool_use", "id": c["id"], "name": c["name"], "input": args if isinstance(args, dict) else {}})
        stop = "tool_use" if calls and finish != "length" else {"length": "max_tokens", "tool_calls": "tool_use"}.get(finish or "", "end_turn")
        yield {"kind": "message", "content": content, "stop_reason": stop, "usage": usage}


def _http_error(status_code: int, text: str, model: str) -> LLMError:
    try:
        body = json.loads(text)
        err = body[0] if isinstance(body, list) and body else body
        msg = (err.get("error") or {}).get("message") if isinstance(err.get("error"), dict) else err.get("error") or err.get("message")
    except (ValueError, AttributeError):
        msg = None
    msg = (str(msg) if msg else text[:300]).strip()
    if status_code in (401, 403):
        return LLMError("Your AI provider rejected the API key or doesn't allow this model. Update it in Settings → AI provider.")
    if status_code == 404:
        return LLMError(f"Model '{model}' or the provider's address wasn't found. Check the model name and base URL in Settings → AI provider.")
    if status_code == 429:
        return LLMError("Your AI provider is rate-limiting requests or the account is out of credit. Wait a minute and try again.")
    return LLMError(f"The AI provider returned an error ({status_code}): {msg}")


def build_llm(provider: str, api_key: str, model: str, base_url: str | None = None) -> LLM:
    from .providers import resolve
    r = resolve(provider, base_url)
    if r.kind == "anthropic":
        return AnthropicLLM(api_key, model, r.base_url)
    if not r.base_url:
        raise LLMError(f"{r.label} needs a base URL. Add it in Settings → AI provider.")
    return OpenAICompatLLM(api_key, model, r.base_url, r.auth)
