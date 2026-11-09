"""AI credit usage (26 Oct 2026): every model call is recorded and counted in credits.

1 credit = 1,000 tokens the model reads or writes (cached re-reads count 10%), see
`providers.credits_for`. Only consumption is shown: an API key is pay-as-you-go, so there is no
monthly allowance (owner, 26 Oct).

`metered(llm, cfg, ...)` wraps the workspace's model; each finished call (the "message" event)
writes one `AIUsage` row in its own session, so it works from background threads too.
`tag(llm, "generate", plan_id=...)` counts the same model as another operation. Recording never
breaks the AI call.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from ..models import AIProviderConfig, AIUsage, User
from .providers import credits_for, resolve

log = logging.getLogger("nowbuilder.ai_usage")

OPERATIONS = {
    "chat": "Chat and planning",
    "generate": "Plan generation",
    "fix": "Fix with AI",
    "auto_repair": "Automatic repair",
}


class MeteredLLM:
    def __init__(self, inner, meta: dict, operation: str, chat_id: str | None = None, plan_id: str | None = None):
        self.inner, self.meta, self.operation, self.chat_id, self.plan_id = inner, meta, operation, chat_id, plan_id

    def tagged(self, operation: str, plan_id: str | None = None) -> MeteredLLM:
        return MeteredLLM(self.inner, self.meta, operation, self.chat_id, plan_id or self.plan_id)

    def stream(self, *args, **kwargs) -> Iterator[dict]:
        for ev in self.inner.stream(*args, **kwargs):
            if ev.get("kind") == "message" and ev.get("usage"):
                self._record(ev["usage"])
            yield ev

    def _record(self, usage: dict) -> None:
        from ..db import SessionLocal
        try:
            db = SessionLocal()
            try:
                m = self.meta
                db.add(AIUsage(workspace_id=m["workspace_id"], user_id=m.get("user_id"), operation=self.operation, provider=m["provider"],
                               model=m["model"], chat_id=self.chat_id, plan_id=self.plan_id,
                               input_tokens=int(usage.get("input") or 0), output_tokens=int(usage.get("output") or 0),
                               cache_read_tokens=int(usage.get("cache_read") or 0), cache_write_tokens=int(usage.get("cache_write") or 0),
                               credits=credits_for(usage)))
                db.commit()
            finally:
                db.close()
        except Exception:  # noqa: BLE001  (usage is bookkeeping; never fail the AI call over it)
            log.warning("Couldn't record AI usage", exc_info=True)


def metered(llm, cfg: AIProviderConfig, *, user_id: str | None, operation: str, chat_id: str | None = None, plan_id: str | None = None):
    """The workspace's model, recording usage. Reads what it needs from `cfg` now (the request's
    session may be closed when the call happens)."""
    if llm is None or cfg is None:
        return llm
    meta = {"workspace_id": cfg.workspace_id, "user_id": user_id, "provider": provider_name(cfg), "model": cfg.model}
    return MeteredLLM(llm, meta, operation, chat_id, plan_id)


def tag(llm, operation: str, plan_id: str | None = None):
    """The same model counted as another operation (no-op for unmetered test models)."""
    return llm.tagged(operation, plan_id) if isinstance(llm, MeteredLLM) else llm


def provider_name(cfg: AIProviderConfig) -> str:
    return (cfg.provider_name or "").strip() or resolve(cfg.provider, cfg.base_url).label


def row_credits(r: AIUsage) -> float:
    if r.credits is not None:
        return r.credits
    return credits_for({"input": r.input_tokens, "output": r.output_tokens, "cache_read": r.cache_read_tokens, "cache_write": r.cache_write_tokens})


# ---------- the usage view ----------

def month_range(month: str | None) -> tuple[datetime, datetime, str]:
    now = datetime.now(UTC)
    try:
        y, m = (int(x) for x in (month or "").split("-"))
        start = datetime(y, m, 1, tzinfo=UTC)
    except ValueError:
        start = datetime(now.year, now.month, 1, tzinfo=UTC)
    end = datetime(start.year + (start.month == 12), start.month % 12 + 1, 1, tzinfo=UTC)
    return start, end, f"{start:%Y-%m}"


def summary(db, workspace_id: str, model: str | None, month: str | None = None) -> dict:
    start, end, label = month_range(month)
    rows = list(db.scalars(select(AIUsage).where(AIUsage.workspace_id == workspace_id, AIUsage.created_at >= start, AIUsage.created_at < end)))
    people = {u.id: f"{u.first_name} {u.last_name}".strip() or u.email
              for u in db.scalars(select(User).where(User.id.in_({r.user_id for r in rows if r.user_id})))}
    used, calls = 0.0, 0
    by_op: dict[str, float] = defaultdict(float)
    by_user: dict[str, float] = defaultdict(float)
    by_day: dict[str, float] = defaultdict(float)
    for r in rows:
        c = row_credits(r)
        created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=UTC)
        used += c
        calls += 1
        by_op[r.operation] += c
        by_user[r.user_id or ""] += c
        by_day[created.date().isoformat()] += c

    days, d = [], start.date()
    last = min(end, datetime.now(UTC) + timedelta(days=1)).date()
    while d < last:
        days.append({"date": d.isoformat(), "credits": round(by_day.get(d.isoformat(), 0.0))})
        d += timedelta(days=1)
    prev = datetime(start.year - (start.month == 1), (start.month - 2) % 12 + 1, 1, tzinfo=UTC)
    used_r = round(used)
    return {
        "month": label, "previous": f"{prev:%Y-%m}", "next": f"{end:%Y-%m}" if end <= datetime.now(UTC) else None,
        "current": label == f"{datetime.now(UTC):%Y-%m}",
        "model": model, "used": used_r, "calls": calls,
        "by_operation": sorted(({"key": k, "label": OPERATIONS.get(k, k), "credits": round(v)} for k, v in by_op.items()), key=lambda x: -x["credits"]),
        "by_member": sorted(({"user_id": k or None, "name": people.get(k, "Someone who left"), "credits": round(v)} for k, v in by_user.items()), key=lambda x: -x["credits"]),
        "by_day": days,
    }


def month_totals(db, workspace_ids: list[str]) -> dict[str, dict]:
    """This month's credits per workspace (Platform page)."""
    start, end, _ = month_range(None)
    out: dict[str, dict] = {}
    if not workspace_ids:
        return out
    for r in db.scalars(select(AIUsage).where(AIUsage.workspace_id.in_(workspace_ids), AIUsage.created_at >= start, AIUsage.created_at < end)):
        b = out.setdefault(r.workspace_id, {"credits": 0.0, "calls": 0})
        b["credits"] += row_credits(r)
        b["calls"] += 1
    for b in out.values():
        b["credits"] = round(b["credits"])
    return out
