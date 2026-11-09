"""Platform administration (owner's design, 19 Oct 2026).

Two levels of admin:
- **Platform admins** (`NOWBUILDER_PLATFORM_ADMINS`, set only on the server) look after every workspace:
  they approve new workspaces, choose each one's plan, override its limits, and turn it off or on.
- **Workspace owners and admins** manage their own team, inside the limits the platform admin set.

A workspace's limits are its plan's numbers unless the platform admin set an override. The
standard plan uses `NOWBUILDER_MAX_INSTANCES` / `NOWBUILDER_MAX_MEMBERS`. Lowering a limit below what a
workspace already uses removes nothing: it only stops new instances or members until they're under it.
With approval sign-up (`NOWBUILDER_SIGNUP_MODE=approval`, the default outside development) a new
person's workspace is `pending` until a platform admin approves it.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (AIProviderConfig, AIUsage, Chat, FixProposal, Integration, Invite, Membership,
                      Message, Plan, PlatformAdmin, Instance, User, Workspace)

# Plan id -> (label, instances, members). "standard" comes from the server settings.
PLANS: dict[str, tuple[str, int, int]] = {
    "starter": ("Starter", 1, 2),
    "team": ("Team", 3, 4),
    "business": ("Business", 5, 10),
}
STATUSES = ("active", "pending", "suspended")
MAX_LIMIT = 500


def plans() -> list[dict]:
    s = get_settings()
    out = [{"id": "standard", "label": "Standard", "instances": s.max_instances, "members": s.max_members}]
    return out + [{"id": k, "label": label, "instances": o, "members": m} for k, (label, o, m) in PLANS.items()]


def plan_of(ws: Workspace) -> dict:
    return next((p for p in plans() if p["id"] == (ws.plan or "standard")), plans()[0])


def limits_of(ws: Workspace) -> tuple[int, int]:
    """(max instances, max members) for this workspace: the override if set, else its plan's."""
    p = plan_of(ws)
    return (ws.max_instances if ws.max_instances is not None else p["instances"], ws.max_members if ws.max_members is not None else p["members"])


def status_of(ws: Workspace) -> str:
    return ws.status or "active"


def new_workspace_status(user: User) -> str:
    return "pending" if get_settings().signup_needs_approval and not user.is_platform_admin else "active"


# ---------- the Platform page ----------

def _iso(dt: datetime | None) -> str | None:
    return None if dt is None else (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


def workspace_row(db: Session, ws: Workspace) -> dict:
    owner = db.get(User, ws.owner_id)
    p = plan_of(ws)
    max_instances, max_members = limits_of(ws)
    members = db.scalar(select(func.count()).select_from(Membership).where(Membership.workspace_id == ws.id, Membership.status == "active")) or 0
    invites = sum(1 for i in db.scalars(select(Invite).where(Invite.workspace_id == ws.id, Invite.status == "pending"))
                  if (i.expires_at if i.expires_at.tzinfo else i.expires_at.replace(tzinfo=UTC)) > datetime.now(UTC))
    n_inst = db.scalar(select(func.count()).select_from(Instance).where(Instance.workspace_id == ws.id)) or 0
    last = db.scalar(select(func.max(Chat.updated_at)).where(Chat.workspace_id == ws.id))
    return {
        "id": ws.id, "name": ws.name, "status": status_of(ws),
        "owner": {"name": f"{owner.first_name} {owner.last_name}".strip() if owner else "", "email": owner.email if owner else ""},
        "plan": p["id"], "plan_label": p["label"],
        "instances": {"max": max_instances, "used": n_inst, "custom": ws.max_instances is not None},
        "members": {"max": max_members, "used": members, "invites": invites, "custom": ws.max_members is not None},
        "created_at": _iso(ws.created_at), "approved_at": _iso(ws.approved_at), "approved_by": ws.approved_by,
        "last_activity_at": _iso(last), "note": ws.platform_note or "",
        "platform_admin": bool(owner and owner.is_platform_admin),
        # the owner works in another workspace now (left over from before 22 Oct, or they joined a team)
        "in_use": _owner_uses(db, ws, owner),
        "ai_month": _ai_month(db, ws.id),
    }


def _ai_month(db: Session, workspace_id: str) -> dict:
    from ..ai.usage import month_totals
    return month_totals(db, [workspace_id]).get(workspace_id) or {"credits": 0, "calls": 0}


def _owner_uses(db: Session, ws: Workspace, owner: User | None) -> bool:
    if owner is None:
        return False
    current = db.scalar(select(Membership.workspace_id).where(Membership.user_id == owner.id, Membership.status.in_(("active", "disabled")))
                        .order_by(Membership.created_at.desc()))
    return current == ws.id


def list_workspaces(db: Session) -> list[dict]:
    """Every workspace that still has an active or turned-off member, waiting ones first, then newest."""
    live = set(db.scalars(select(Membership.workspace_id).where(Membership.status.in_(("active", "disabled")))))

    def shown(w: Workspace) -> bool:
        if w.id not in live or status_of(w) == "closed":
            return False
        if status_of(w) == "pending":  # sign-ups appear once they've confirmed their email
            owner = db.get(User, w.owner_id)
            return bool(owner and owner.email_verified)
        return True
    rows = [workspace_row(db, w) for w in db.scalars(select(Workspace).order_by(Workspace.created_at.desc())) if shown(w)]
    order = {"pending": 0, "active": 1, "suspended": 2}
    return sorted(rows, key=lambda r: order.get(r["status"], 3))


class PlatformError(Exception):
    """Shown as 400 with this message."""


def update_workspace(db: Session, admin: User, ws: Workspace, *, plan: str | None = None, max_instances: int | None | str = "keep",
                     max_members: int | None | str = "keep", status: str | None = None, note: str | None = None) -> Workspace:
    if plan is not None:
        if plan not in {p["id"] for p in plans()}:
            raise PlatformError("Choose one of the plans.")
        ws.plan = None if plan == "standard" else plan
    for field, value in (("max_instances", max_instances), ("max_members", max_members)):
        if value == "keep":
            continue
        if value is not None and not (isinstance(value, int) and 1 <= value <= MAX_LIMIT):
            raise PlatformError(f"Limits must be between 1 and {MAX_LIMIT}.")
        setattr(ws, field, value)
    if status is not None:
        if status not in STATUSES or status == "pending":
            raise PlatformError("Status must be active or suspended.")
        owner = db.get(User, ws.owner_id)
        if status == "suspended" and owner is not None and owner.is_platform_admin:
            raise PlatformError("A platform admin's workspace can't be turned off.")
        approving = status == "active" and status_of(ws) == "pending"
        if approving:
            ws.approved_at, ws.approved_by = datetime.now(UTC), admin.email
        ws.status = status
        if approving and owner is not None:
            from . import mailer
            db.flush()
            n_inst, n_members = limits_of(ws)
            mailer.send_later(mailer.approved(owner.email, owner.first_name, ws.name, n_inst, n_members, get_settings().public_url.rstrip("/") + "/"))
    if note is not None:
        ws.platform_note = note.strip()[:500] or None
    db.commit()
    return ws


def counts(rows: list[dict]) -> dict:
    return {k: sum(1 for r in rows if r["status"] == k) for k in STATUSES}


# ---------- platform admins ----------

def admins(db: Session, me: User) -> list[dict]:
    """Everyone with platform admin rights: from the server setting first, then those added in the app."""
    out: list[dict] = []
    def person(email: str) -> dict:
        u = db.scalar(select(User).where(func.lower(User.email) == email))
        return {"email": email, "name": f"{u.first_name} {u.last_name}".strip() if u else "", "signed_up": u is not None,
                "is_me": email == me.email.strip().lower()}
    for email in sorted(get_settings().platform_admin_emails):
        out.append({**person(email), "source": "server", "added_by": None, "added_at": None})
    for a in db.scalars(select(PlatformAdmin).order_by(PlatformAdmin.created_at)):
        if a.email not in get_settings().platform_admin_emails:
            out.append({**person(a.email), "source": "app", "added_by": a.added_by, "added_at": _iso(a.created_at)})
    return out


def add_admin(db: Session, me: User, email: str) -> None:
    email = email.strip().lower()
    if email in get_settings().platform_admin_emails or db.scalar(select(PlatformAdmin.id).where(PlatformAdmin.email == email)):
        raise PlatformError(f"{email} is already a platform admin.")
    db.add(PlatformAdmin(email=email, added_by=me.email))
    db.commit()


def remove_admin(db: Session, me: User, email: str) -> None:
    email = email.strip().lower()
    if email in get_settings().platform_admin_emails:
        raise PlatformError(f"{email} is set on the server (NOWBUILDER_PLATFORM_ADMINS). Remove it there and restart nowBuilder.")
    if email == me.email.strip().lower():
        raise PlatformError("You can't remove yourself. Ask another platform admin.")
    a = db.scalar(select(PlatformAdmin).where(PlatformAdmin.email == email))
    if a is None:
        raise PlatformError(f"{email} isn't a platform admin.")
    db.delete(a)
    db.commit()


# ---------- deleting a workspace ----------

def delete_workspace(db: Session, me: User, ws: Workspace, confirm: str) -> str:
    """Delete a workspace and everything in it, for good. Its people keep their accounts; next time
    they sign in they get a new workspace of their own (waiting for approval with approval sign-up).
    ServiceNow itself isn't touched: what was deployed stays in the instances."""
    import shutil
    from pathlib import Path

    if confirm.strip() != ws.name:
        raise PlatformError(f"Type the workspace name ({ws.name}) to confirm.")
    mine = db.scalar(select(Membership.workspace_id).where(Membership.user_id == me.id, Membership.status.in_(("active", "disabled")))
                     .order_by(Membership.created_at.desc()))
    if mine == ws.id:
        raise PlatformError("This is the workspace you're using, so it can't be deleted here.")
    data = Path(get_settings().data_dir)
    instance_ids = list(db.scalars(select(Instance.id).where(Instance.workspace_id == ws.id)))
    chat_ids = list(db.scalars(select(Chat.id).where(Chat.workspace_id == ws.id)))
    plan_ids = list(db.scalars(select(Plan.id).where(Plan.chat_id.in_(chat_ids or [""]))))
    for pid in plan_ids:
        shutil.rmtree(data / "rollbacks" / pid, ignore_errors=True)
    deletes = [
        (FixProposal, FixProposal.plan_id.in_(plan_ids or [""])), (Plan, Plan.id.in_(plan_ids or [""])),
        (Message, Message.chat_id.in_(chat_ids or [""])), (Chat, Chat.id.in_(chat_ids or [""])),
        (Instance, Instance.id.in_(instance_ids or [""])),
        (AIProviderConfig, AIProviderConfig.workspace_id == ws.id), (Integration, Integration.workspace_id == ws.id),
        (AIUsage, AIUsage.workspace_id == ws.id),
        (Invite, Invite.workspace_id == ws.id),
        (Membership, Membership.workspace_id == ws.id),
    ]
    from sqlalchemy import delete
    for model, where in deletes:
        db.execute(delete(model).where(where))
    name = ws.name
    db.delete(ws)
    db.commit()
    return name
