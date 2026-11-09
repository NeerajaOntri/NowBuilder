"""One chat turn: the model answers, reading the connected instance with tools; events stream to the browser.

Events yielded to the client (Server-Sent Events):
  {"type": "status", "text": str}        progress line ("Reading fields on incident…")
  {"type": "text", "delta": str}         reply text as it streams
  {"type": "plan_draft", "plan": {...}}  the plan card filling in while the model writes it
  {"type": "plan", "plan": {...}}        the plan was saved; rows are "planned"
  {"type": "component", "plan_id", "component"}   one artifact started, finished or failed
  {"type": "plan_done", "plan": {...}}   every artifact generated
  {"type": "error", "message": str}

A plan is proposed by the model calling `propose_plan`; `PlanBuilder` (ai/planning.py) saves it,
generates each record and script, checks them, and (when the instance allows it) deploys them into
the instance straight away. `deploy_plan` deploys a plan already on screen when the user asks.
"""
from __future__ import annotations

from collections.abc import Generator, Iterator
from dataclasses import dataclass, field
from datetime import date

from ..services.servicenow import ServiceNowClient
from .llm import LLM, LLMError
from .planning import PlanBuilder, draft_from_snapshot
from .skills import Skills
from .tools import ToolRunner

MAX_MODEL_CALLS = 10
PLAN_TOOL = "propose_plan"
DEPLOY_TOOL = "deploy_plan"


@dataclass
class TurnResult:
    text: str = ""
    activity: list[str] = field(default_factory=list)
    plan_id: str | None = None
    error: str | None = None


@dataclass
class ChatContext:
    instance_summary: str | None          # one paragraph about the connected instance, or None


def build_context(ctx: ChatContext) -> str:
    lines = ["# Context", f"Today: {date.today().isoformat()}"]
    if ctx.instance_summary:
        lines.append(f"Connected instance: {ctx.instance_summary}")
    else:
        lines.append("Connected instance: none. The instance tools will report that no instance is connected.")
    return "\n".join(lines)


def _last_user_text(history: list[dict]) -> str:
    for m in reversed(history):
        if m["role"] == "user" and isinstance(m["content"], str):
            return m["content"][:4000]
    return ""


class ChatTurn:
    def __init__(self, llm: LLM, skills: Skills, client: ServiceNowClient | None, ctx: ChatContext,
                 history: list[dict], planner: PlanBuilder | None = None):
        self.llm, self.skills, self.client, self.ctx = llm, skills, client, ctx
        self.runner = ToolRunner(skills, client)
        self.planner = planner
        self.messages = list(history)
        self.result = TurnResult()
        prompt = skills.build_prompt("chat", text=_last_user_text(history))
        self.system, self.skills_used = prompt.system, prompt.skills
        # Without a planner (no workspace session) the model can still answer, it just can't plan.
        self.tools = prompt.tools if planner else [t for t in prompt.tools if t["name"] not in (PLAN_TOOL, DEPLOY_TOOL)]
        # Deploying happens on the plan card's Deploy button unless automatic deployment is on:
        # the model then has no way to deploy, whatever the message says.
        if planner is not None and getattr(planner, "deployer", None) is None:
            self.tools = [t for t in self.tools if t["name"] != DEPLOY_TOOL]

    def _status(self, text: str) -> dict:
        self.result.activity.append(text)
        return {"type": "status", "text": text}

    def run(self) -> Iterator[dict]:
        context = build_context(self.ctx)
        try:
            for _ in range(MAX_MODEL_CALLS):
                final: dict | None = None
                drafted = ""
                for ev in self.llm.stream(self.system, context, self.messages, self.tools):
                    if ev["kind"] == "text":
                        self.result.text += ev["delta"]
                        yield {"type": "text", "delta": ev["delta"]}
                    elif ev["kind"] == "tool_input" and ev.get("name") == PLAN_TOOL and self.planner:
                        draft = draft_from_snapshot(ev.get("snapshot") or {})
                        # only send a draft that actually changed, so the card doesn't flicker
                        if draft and (key := str(draft)) != drafted:
                            drafted = key
                            yield {"type": "plan_draft", "plan": draft}
                    elif ev["kind"] == "message":
                        final = ev
                if final is None:
                    raise LLMError("The AI response ended unexpectedly. Try again.")

                self.messages.append({"role": "assistant", "content": final["content"]})
                tool_uses = [b for b in final["content"] if b["type"] == "tool_use"]
                if final["stop_reason"] == "max_tokens" and not tool_uses:
                    yield {"type": "text", "delta": "\n\n_(Reply cut off because it was too long.)_"}
                if not tool_uses:
                    return
                results: list[dict] = []
                for tu in tool_uses:
                    if tu["name"] == PLAN_TOOL and self.planner:
                        yield self._status("Putting the plan together")
                        content, is_error = yield from self._plan(tu["input"])
                    elif tu["name"] == DEPLOY_TOOL and self.planner:
                        content, is_error = yield from self._deploy((tu.get("input") or {}).get("plan_id"))
                    else:
                        yield self._status(self.runner.describe(tu["name"], tu["input"]))
                        content, is_error = self.runner.run(tu["name"], tu["input"])
                    results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": content,
                                    **({"is_error": True} if is_error else {})})
                self.messages.append({"role": "user", "content": results})
            yield {"type": "text", "delta": "\n\nI stopped here because this took too many steps. Try narrowing the request."}
        except LLMError as e:
            self.result.error = str(e)
            yield {"type": "error", "message": str(e)}

    def _deploy(self, plan_id: str | None) -> Generator[dict, None, tuple[str, bool]]:
        assert self.planner is not None
        for ev in self.planner.deploy_existing(plan_id):
            yield self._status(ev["text"]) if ev["type"] == "status" else ev
        if self.planner.plan_id:
            self.result.plan_id = self.result.plan_id or self.planner.plan_id
        return self.planner.tool_result or "Nothing was deployed.", False

    def _plan(self, proposal: dict) -> Generator[dict, None, tuple[str, bool]]:
        """Save and generate the plan, passing its events on. Returns the tool result for the model."""
        assert self.planner is not None
        for ev in self.planner.build(proposal):
            if ev["type"] == "status":
                yield self._status(ev["text"])
            else:
                yield ev
        if self.planner.plan_id:
            self.result.plan_id = self.planner.plan_id
            return self.planner.tool_result, False
        return self.planner.tool_result or "The plan couldn't be built.", True
