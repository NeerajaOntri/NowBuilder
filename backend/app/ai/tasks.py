"""Run a model task that must end in one JSON object (generation, Fix with AI), with tool use and retries."""
from __future__ import annotations

import json
import re
from collections.abc import Callable

import jsonschema

from .llm import LLM, LLMError
from .tools import ToolRunner

MAX_CALLS = 12


class TaskError(Exception):
    """The model couldn't produce a usable result; the message is safe to show."""


def extract_json(text: str) -> dict:
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", t)
    if fence:
        t = fence.group(1)
    else:
        start, end = t.find("{"), t.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object found in the reply.")
        t = t[start:end + 1]
    data = json.loads(t)
    if not isinstance(data, dict):
        raise ValueError("The reply must be one JSON object.")
    return data


def run_json_task(llm: LLM, system: str, context: str, user_content: str, tools: list[dict], runner: ToolRunner,
                  schema: dict, *, on_status: Callable[[str], None] = lambda s: None,
                  extra_check: Callable[[dict], list[str]] | None = None, max_fixes: int = 2, max_tokens: int = 16000) -> dict:
    messages: list[dict] = [{"role": "user", "content": user_content}]
    validator = jsonschema.Draft202012Validator(schema)
    fixes_left = max_fixes
    for _ in range(MAX_CALLS):
        final = None
        for ev in llm.stream(system, context, messages, tools, max_tokens=max_tokens):
            if ev["kind"] == "message":
                final = ev
        if final is None:
            raise LLMError("The AI response ended unexpectedly. Try again.")
        messages.append({"role": "assistant", "content": final["content"]})
        tool_uses = [b for b in final["content"] if b["type"] == "tool_use"]
        if tool_uses:
            results = []
            for tu in tool_uses:
                on_status(runner.describe(tu["name"], tu["input"]))
                content, is_error = runner.run(tu["name"], tu["input"])
                results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": content, **({"is_error": True} if is_error else {})})
            messages.append({"role": "user", "content": results})
            continue
        text = "".join(b.get("text", "") for b in final["content"] if b["type"] == "text")
        if final.get("stop_reason") == "max_tokens":
            problems = ["Your reply was cut off because it was too long. Return the same JSON more compactly (no comments, no extra whitespace)."]
        else:
            try:
                data = extract_json(text)
                problems = [f'{"/".join(map(str, e.absolute_path)) or "root"}: {e.message}' for e in validator.iter_errors(data)][:15]
                if not problems and extra_check:
                    problems = extra_check(data)
                if not problems:
                    return data
            except ValueError as e:
                problems = [f"Your reply wasn't valid JSON: {e}"]
        if fixes_left <= 0:
            raise TaskError("The AI's answer didn't pass nowBuilder's checks: " + "; ".join(problems[:3]))
        fixes_left -= 1
        on_status("Correcting the AI's output")
        messages.append({"role": "user", "content": "nowBuilder couldn't accept that reply. Fix these problems and reply with the complete JSON object only:\n- " + "\n- ".join(problems)})
    raise TaskError("The AI took too many steps. Try again.")
