"""Workspace, members and invites (Admin section)."""
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from ..config import get_settings
from ..deps import DB, CurrentUser, WorkspaceCtx
from ..models import Membership, User, Workspace
from ..services import workspace as ws
from ..services.workspace import Ctx

router = APIRouter(prefix="/api", tags=["workspace"])


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class InviteIn(BaseModel):
    email: EmailStr
    role: str
    instance_ids: list[str] | None = None  # None = every instance


class MemberIn(BaseModel):
    role: str | None = None
    instance_ids: list[str] | None = None
    all_instances: bool | None = None  # true = every instance (instance_ids ignored)
    status: str | None = None


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


def _name(u: User | None) -> str:
    return f"{u.first_name} {u.last_name}".strip() if u else "Someone"


def me_out(ctx: Ctx) -> dict:
    return {
        "workspace": {"id": ctx.workspace.id, "name": ctx.workspace.name},
        "me": {"member_id": ctx.member.id, "role": ctx.role, "role_label": ws.ROLE_LABEL[ctx.role],
               "permissions": sorted(ws.PERMISSIONS[ctx.role]), "instance_ids": sorted(ctx.instance_ids()),
               "all_instances": ctx.role in ("owner", "admin") or ctx.member.instance_ids is None},
        "limits": ws.limits(ctx.db, ctx),
        "roles": [{"id": r, "label": ws.ROLE_LABEL[r], "permissions": sorted(ws.PERMISSIONS[r])} for r in ws.ROLES],
    }


def _link(token: str) -> str:
    return f"{get_settings().public_url.rstrip('/')}/invite/{token}"


def _invite_out(db, inv) -> dict:
    expired = (inv.expires_at if inv.expires_at.tzinfo else inv.expires_at.replace(tzinfo=UTC)) <= datetime.now(UTC)
    return {"id": inv.id, "email": inv.email, "role": inv.role, "instance_ids": inv.instance_ids, "status": "expired" if inv.status == "pending" and expired else inv.status,
            "expires_at": _iso(inv.expires_at), "created_at": _iso(inv.created_at), "invited_by": _name(db.get(User, inv.created_by))}


@router.get("/workspace")
def get_workspace(ctx: WorkspaceCtx) -> dict:
    """Who I am in this workspace: role, permissions, the instances I can use, and the limits."""
    return me_out(ctx)


@router.patch("/workspace")
def rename_workspace(body: WorkspaceIn, ctx: WorkspaceCtx, db: DB) -> dict:
    ctx.require("manage_members")
    ctx.workspace.name = body.name.strip()
    db.commit()
    return me_out(ctx)


@router.get("/workspace/members")
def list_members(ctx: WorkspaceCtx, db: DB) -> dict:
    """Members and invites. Every member can see who's in the workspace; only admins see invites."""
    rows = db.scalars(select(Membership).where(Membership.workspace_id == ctx.workspace.id, Membership.status.in_(("active", "disabled")))
                      .order_by(Membership.created_at))
    members = []
    for m in rows:
        u = db.get(User, m.user_id)
        members.append({"id": m.id, "user_id": m.user_id, "name": _name(u), "email": u.email if u else "", "role": m.role,
                        "status": m.status, "instance_ids": None if m.role in ("owner", "admin") else m.instance_ids,
                        "joined_at": _iso(m.created_at), "is_me": m.user_id == ctx.user.id})
    invites = []
    if ctx.can("manage_members"):
        from ..models import Invite
        invites = [_invite_out(db, i) for i in db.scalars(select(Invite).where(Invite.workspace_id == ctx.workspace.id, Invite.status == "pending")
                                                            .order_by(Invite.created_at.desc()))]
    return {"members": members, "invites": invites, "limits": ws.limits(db, ctx),
            "instances": [{"id": o.id, "name": o.name, "instance_type": o.instance_type} for o in ctx.all_instances()]}


def _email_invite(ctx: Ctx, inv, token: str) -> bool:
    """Send the invite link by email too (best effort; the link can always be copied). True when sent."""
    from ..services import mailer
    s = get_settings()
    if not s.smtp_host.strip() and not s.dev_outbox:
        return False
    mailer.send_later(mailer.invite(inv.email, _name(ctx.user), ctx.workspace.name, ws.ROLE_LABEL.get(inv.role, inv.role), _link(token), s.invite_days))
    return True


@router.post("/workspace/invites", status_code=status.HTTP_201_CREATED)
def create_invite(body: InviteIn, ctx: WorkspaceCtx, db: DB) -> dict:
    inv, token = ws.new_invite(ctx, body.email, body.role, body.instance_ids)
    return {"invite": _invite_out(db, inv), "link": _link(token), "emailed": _email_invite(ctx, inv, token)}


@router.post("/workspace/invites/{invite_id}/renew")
def renew_invite(invite_id: str, ctx: WorkspaceCtx, db: DB) -> dict:
    """A fresh link for a pending invite (the old link stops working)."""
    inv, token = ws.renew_invite(ctx, invite_id)
    return {"invite": _invite_out(db, inv), "link": _link(token), "emailed": _email_invite(ctx, inv, token)}


@router.delete("/workspace/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(invite_id: str, ctx: WorkspaceCtx) -> None:
    ws.revoke_invite(ctx, invite_id)


@router.patch("/workspace/members/{member_id}")
def update_member(member_id: str, body: MemberIn, ctx: WorkspaceCtx) -> dict:
    instance_ids = None if body.all_instances else (body.instance_ids if body.instance_ids is not None else "keep")
    ws.update_member(ctx, member_id, role=body.role, instance_ids=instance_ids, status=body.status)
    return {"ok": True}


@router.delete("/workspace/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(member_id: str, ctx: WorkspaceCtx) -> None:
    ws.remove_member(ctx, member_id)


# ---------- invite links (the invited person) ----------

@router.get("/invites/{token}")
def view_invite(token: str, db: DB) -> dict:
    """Public: what the invite is for, so the page can say who invited whom before sign-in."""
    inv = ws.find_invite(db, token)
    problem = ws.invite_problem(inv)
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, problem)
    wsp = db.get(Workspace, inv.workspace_id)
    return {"workspace": wsp.name if wsp else "", "email": inv.email, "role": inv.role, "role_label": ws.ROLE_LABEL.get(inv.role, inv.role),
            "invited_by": _name(db.get(User, inv.created_by)), "problem": problem, "has_account": bool(db.scalar(select(User.id).where(User.email == inv.email)))}


@router.post("/invites/{token}/accept")
def accept_invite(token: str, user: CurrentUser, db: DB) -> dict:
    ws.accept_invite(db, user, token)
    return me_out(ws.context(db, user))

