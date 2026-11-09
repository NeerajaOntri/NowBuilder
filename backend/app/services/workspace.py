"""Workspaces, members, roles and limits (carried over from MetaFlow).

- One workspace per person. A new user gets their own workspace (as Owner) on first use; their
  existing instances, chats and AI provider move into it. Accepting an invite moves them into the
  inviting workspace instead.
- Everything (instances, AI provider, chats, plans) belongs to the workspace. Members see the chats
  and plans of the instances they can use (a shared team space).
- Limits: at most N active members, counting pending invites, and at most M connected ServiceNow
  instances per workspace. N and M come from the workspace's plan or a platform admin's override
  (services/platform.py); the standard plan uses `max_members` (3) / `max_instances` (2).
- A workspace can be pending (waiting for a platform admin's approval) or suspended; its members then
  get 403 with a code the frontend shows as a waiting / turned-off screen.
- Roles decide what a member can do; every route checks on the server (`Ctx.require`).
"""
from __future__ import annotations

import hashlib
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AIProviderConfig, Chat, Invite, Membership, Instance, User, Workspace

ROLES = ("owner", "admin", "developer", "reviewer", "viewer")
ROLE_LABEL = {"owner": "Owner", "admin": "Admin", "developer": "Developer", "reviewer": "Reviewer", "viewer": "Viewer"}

# What each role can do. "deploy" = development and test instances; "deploy_prod" = production.
PERMISSIONS: dict[str, set[str]] = {
    "owner": {"read", "build", "approve", "deploy", "deploy_prod", "push", "sync", "manage_instances", "manage_ai", "manage_members", "manage_integrations"},
    "admin": {"read", "build", "approve", "deploy", "deploy_prod", "push", "sync", "manage_instances", "manage_ai", "manage_members", "manage_integrations"},
    "developer": {"read", "build", "approve", "deploy", "deploy_prod", "push", "sync"},  # developers deploy to production too (as in MetaFlow)
    "reviewer": {"read", "approve", "sync"},  # reviewers review and approve, they don't deploy
    "viewer": {"read"},
}
DENIED = {
    "build": "Your role can't build or change plans. Ask a workspace admin for the Developer role.",
    "approve": "Your role can't approve plans.",
    "deploy": "Your role can't deploy. Ask a Developer, Admin or Owner to deploy this plan.",
    "deploy_prod": "Your role can't deploy to production. Ask a Developer, Admin or Owner to deploy this plan.",
    "sync": "Your role can't refresh instance data.",
    "manage_instances": "Only workspace admins can connect, change or remove ServiceNow instances.",
    "manage_ai": "Only workspace admins can change the AI provider.",
    "manage_members": "Only workspace admins can manage members.",
    "manage_integrations": "Only workspace admins can connect Jira or GitHub.",
    "push": "Your role can't push to Git. Ask a Developer, Admin or Owner.",
}


class AccessError(Exception):
    """Shown to the user as 403 with this message."""


class LimitError(Exception):
    """Shown to the user as 409 with this message."""


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- membership ----------

def active_membership(db: Session, user: User) -> Membership | None:
    return db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.status.in_(("active", "disabled")))
                     .order_by(Membership.created_at.desc()))


_first_use = threading.Lock()


def ensure_membership(db: Session, user: User) -> Membership:
    """The user's membership, creating their own workspace on first use and moving their
    existing instances, chats and AI provider into it.

    The app sends several requests at once when it opens, so this must create exactly one
    workspace: a lock serialises first use within the process, and the database's
    one-active-membership-per-user index (db._one_active_membership) stops a second process."""
    m = active_membership(db, user)
    if m:
        return m
    with _first_use:
        db.expire_all()  # another request may have just created it
        m = active_membership(db, user)
        if m:
            return m
        try:
            return _create_own_workspace(db, user)
        except IntegrityError:
            db.rollback()
            m = active_membership(db, user)
            if m is None:
                raise
            return m


def _create_own_workspace(db: Session, user: User) -> Membership:
    from .platform import new_workspace_status
    ws = Workspace(name=f"{user.first_name}'s workspace", owner_id=user.id, status=new_workspace_status(user))
    db.add(ws)
    db.flush()
    m = Membership(workspace_id=ws.id, user_id=user.id, role="owner", status="active")
    db.add(m)
    db.flush()
    db.execute(update(Instance).where(Instance.user_id == user.id, Instance.workspace_id.is_(None)).values(workspace_id=ws.id))
    db.execute(update(Chat).where(Chat.user_id == user.id, Chat.workspace_id.is_(None)).values(workspace_id=ws.id))
    db.execute(update(AIProviderConfig).where(AIProviderConfig.user_id == user.id, AIProviderConfig.workspace_id.is_(None)).values(workspace_id=ws.id))
    db.commit()
    return m


@dataclass
class Ctx:
    """The signed-in user in their workspace. Every route works through this."""
    db: Session
    user: User
    member: Membership
    workspace: Workspace

    @property
    def role(self) -> str:
        return self.member.role

    def can(self, action: str) -> bool:
        return action in PERMISSIONS.get(self.role, set())

    def require(self, action: str) -> None:
        if not self.can(action):
            raise AccessError(DENIED.get(action, "You don't have access to do that."))

    def require_deploy(self, instance: Instance | None) -> None:
        self.require("deploy_prod" if instance is not None and instance.instance_type == "Production" else "deploy")

    # ----- instances -----
    def all_instances(self) -> list[Instance]:
        return list(self.db.scalars(select(Instance).where(Instance.workspace_id == self.workspace.id).order_by(Instance.created_at)))

    def instance_ids(self) -> set[str]:
        """Instances this member can use."""
        ids = {o.id for o in self.all_instances()}
        if self.role in ("owner", "admin") or self.member.instance_ids is None:
            return ids
        return ids & set(self.member.instance_ids)

    def instances(self) -> list[Instance]:
        allowed = self.instance_ids()
        return [o for o in self.all_instances() if o.id in allowed]

    def instance(self, instance_id: str | None) -> Instance | None:
        """An instance this member can use, or None."""
        if not instance_id:
            return None
        o = self.db.get(Instance, instance_id)
        return o if o is not None and o.workspace_id == self.workspace.id and o.id in self.instance_ids() else None

    def selected_instance(self) -> Instance | None:
        found = self.instances()
        chosen = next((o for o in found if o.id == self.member.selected_instance_id), None)
        return chosen or (found[0] if found else None)

    def select_instance(self, instance: Instance) -> None:
        self.member.selected_instance_id = instance.id

    # ----- chats -----
    def can_see_chat(self, chat: Chat | None) -> bool:
        if chat is None or chat.workspace_id != self.workspace.id:
            return False
        return chat.instance_id is None or chat.instance_id in self.instance_ids() or chat.user_id == self.user.id

    # ----- AI provider -----
    def ai_config(self) -> AIProviderConfig | None:
        return self.db.scalar(select(AIProviderConfig).where(AIProviderConfig.workspace_id == self.workspace.id))


class WorkspacePending(AccessError):
    """The workspace is waiting for a platform admin's approval."""
    code = "pending"


class EmailUnverified(AccessError):
    """The person hasn't typed the code we emailed them yet."""
    code = "unverified"


class WorkspaceSuspended(AccessError):
    """A platform admin turned the workspace off."""
    code = "suspended"


def context(db: Session, user: User) -> Ctx:
    if not user.email_verified:
        raise EmailUnverified(f"Confirm your email first: type the 6-digit code we sent to {user.email}.")
    m = ensure_membership(db, user)
    wsp = db.get(Workspace, m.workspace_id)
    if m.status == "disabled":
        raise AccessError(f"Your access to {wsp.name if wsp else 'this workspace'} is turned off. Ask a workspace admin to turn it back on.")
    state = (wsp.status if wsp else None) or "active"
    if state != "active" and user.is_platform_admin:  # a platform admin's own workspace always works
        wsp.status, state = "active", "active"
        db.commit()
    if state == "pending":
        raise WorkspacePending(f"Thanks for signing up. {wsp.name} is waiting for approval by the nowBuilder team. "
                               "You'll be able to connect your ServiceNow instance and start building as soon as it's approved.")
    if state == "suspended":
        raise WorkspaceSuspended(f"The nowBuilder team has paused {wsp.name}. Your instances, chats and plans are kept. Contact the nowBuilder team to turn it back on.")
    return Ctx(db=db, user=user, member=m, workspace=wsp)


# ---------- limits ----------

def member_count(db: Session, ws_id: str) -> int:
    return db.scalar(select(func.count()).select_from(Membership).where(Membership.workspace_id == ws_id, Membership.status == "active")) or 0


def pending_invites(db: Session, ws_id: str) -> list[Invite]:
    return [i for i in db.scalars(select(Invite).where(Invite.workspace_id == ws_id, Invite.status == "pending"))
            if _aware(i.expires_at) > _now()]


def seats_used(db: Session, ws_id: str) -> int:
    return member_count(db, ws_id) + len(pending_invites(db, ws_id))


def _limits(db: Session, ws_id: str) -> tuple[int, int]:
    from .platform import limits_of
    return limits_of(db.get(Workspace, ws_id))


def check_member_room(db: Session, ws_id: str, extra: int = 1, count_invites: bool = True) -> None:
    cap = _limits(db, ws_id)[1]
    used = seats_used(db, ws_id) if count_invites else member_count(db, ws_id)
    if used + extra > cap:
        raise LimitError(f"This workspace can have at most {cap} members, including pending invites. Remove a member or revoke an invite first.")


def check_instance_room(ctx: Ctx) -> None:
    cap = _limits(ctx.db, ctx.workspace.id)[0]
    if len(ctx.all_instances()) >= cap:
        raise LimitError(f"This workspace can connect at most {cap} ServiceNow instance{'s' if cap != 1 else ''}. Remove one in Settings → ServiceNow instances before connecting another.")


def limits(db: Session, ctx: Ctx) -> dict:
    from .platform import plan_of
    max_instances, max_members = _limits(db, ctx.workspace.id)
    return {"members": {"max": max_members, "active": member_count(db, ctx.workspace.id), "pending": len(pending_invites(db, ctx.workspace.id))},
            "instances": {"max": max_instances, "used": len(ctx.all_instances())}, "plan": plan_of(ctx.workspace)["label"]}


# ---------- invites ----------

def new_invite(ctx: Ctx, email: str, role: str, instance_ids: list[str] | None) -> tuple[Invite, str]:
    ctx.require("manage_members")
    db = ctx.db
    email = email.strip().lower()
    if role not in ROLES or role == "owner":
        raise AccessError("Choose Admin, Developer, Reviewer or Viewer.")
    if role == "admin" and ctx.role != "owner":
        raise AccessError("Only the workspace owner can invite admins.")
    member = db.scalar(select(User).where(func.lower(User.email) == email))
    if member and db.scalar(select(Membership.id).where(Membership.workspace_id == ctx.workspace.id, Membership.user_id == member.id,
                                                        Membership.status.in_(("active", "disabled")))):
        raise LimitError(f"{email} is already a member of this workspace.")
    for old in pending_invites(db, ctx.workspace.id):
        if old.email == email:
            raise LimitError(f"{email} already has a pending invite. Copy its link again or revoke it.")
    check_member_room(db, ctx.workspace.id)
    token = secrets.token_urlsafe(32)
    inv = Invite(workspace_id=ctx.workspace.id, email=email, role=role, instance_ids=_clean_instance_ids(ctx, instance_ids),
                 token_hash=hash_token(token), created_by=ctx.user.id, expires_at=_now() + timedelta(days=get_settings().invite_days))
    db.add(inv)
    db.commit()
    return inv, token


def renew_invite(ctx: Ctx, invite_id: str) -> tuple[Invite, str]:
    ctx.require("manage_members")
    inv = ctx.db.get(Invite, invite_id)
    if not inv or inv.workspace_id != ctx.workspace.id or inv.status != "pending":
        raise LimitError("That invite isn't pending any more.")
    if _aware(inv.expires_at) <= _now():
        check_member_room(ctx.db, ctx.workspace.id)
    token = secrets.token_urlsafe(32)
    inv.token_hash, inv.expires_at = hash_token(token), _now() + timedelta(days=get_settings().invite_days)
    ctx.db.commit()
    return inv, token


def revoke_invite(ctx: Ctx, invite_id: str) -> None:
    ctx.require("manage_members")
    inv = ctx.db.get(Invite, invite_id)
    if not inv or inv.workspace_id != ctx.workspace.id or inv.status != "pending":
        raise LimitError("That invite isn't pending any more.")
    inv.status = "revoked"
    ctx.db.commit()


def find_invite(db: Session, token: str) -> Invite | None:
    return db.scalar(select(Invite).where(Invite.token_hash == hash_token(token)))


def invite_problem(inv: Invite | None) -> str | None:
    if inv is None:
        return "This invite link isn't valid. Ask for a new one."
    if inv.status == "revoked":
        return "This invite was revoked. Ask a workspace admin for a new one."
    if inv.status == "accepted":
        return "This invite was already used."
    if _aware(inv.expires_at) <= _now():
        return "This invite has expired. Ask a workspace admin to send it again."
    return None


def accept_invite(db: Session, user: User, token: str) -> Membership:
    if not user.email_verified:
        raise EmailUnverified(f"Confirm your email first: type the 6-digit code we sent to {user.email}, then join.")
    inv = find_invite(db, token)
    if problem := invite_problem(inv):
        raise LimitError(problem)
    if user.email.strip().lower() != inv.email:
        raise AccessError(f"This invite is for {inv.email}. Sign in with that email address to accept it.")
    current = active_membership(db, user)
    if current and current.workspace_id == inv.workspace_id:
        inv.status, inv.accepted_at = "accepted", _now()
        db.commit()
        return current
    if current:
        if current.role == "owner" and member_count(db, current.workspace_id) > 1:
            raise LimitError("You own a workspace with other members. Remove them before joining another workspace.")
        current.status = "left"
        if current.role == "owner":  # their own workspace is left empty: it no longer needs approval or a plan
            own = db.get(Workspace, current.workspace_id)
            if own is not None:
                own.status = "closed"
    # the invite already holds a seat, so only active members are counted here
    check_member_room(db, inv.workspace_id, extra=1, count_invites=False)
    m = Membership(workspace_id=inv.workspace_id, user_id=user.id, role=inv.role, status="active", instance_ids=inv.instance_ids, invited_by=inv.created_by)
    db.add(m)
    inv.status, inv.accepted_at = "accepted", _now()
    db.commit()
    return m


# ---------- members ----------

def _clean_instance_ids(ctx: Ctx, instance_ids: list[str] | None) -> list[str] | None:
    if instance_ids is None:
        return None
    in_ws = {o.id for o in ctx.all_instances()}
    bad = [o for o in instance_ids if o not in in_ws]
    if bad:
        raise LimitError("One of the chosen instances isn't in this workspace any more. Reload and try again.")
    return sorted(set(instance_ids))


def _member(ctx: Ctx, member_id: str) -> Membership:
    m = ctx.db.get(Membership, member_id)
    if not m or m.workspace_id != ctx.workspace.id or m.status not in ("active", "disabled"):
        raise LimitError("That member isn't in this workspace.")
    return m


def update_member(ctx: Ctx, member_id: str, *, role: str | None = None, instance_ids: list[str] | None | str = "keep", status: str | None = None) -> Membership:
    ctx.require("manage_members")
    m = _member(ctx, member_id)
    if m.role == "owner":
        raise AccessError("The workspace owner's access can't be changed.")
    if m.user_id == ctx.user.id:
        raise AccessError("You can't change your own access. Ask another admin.")
    if m.role == "admin" and ctx.role != "owner":
        raise AccessError("Only the workspace owner can change an admin.")
    if role is not None:
        if role not in ROLES or role == "owner":
            raise AccessError("Choose Admin, Developer, Reviewer or Viewer.")
        if role == "admin" and ctx.role != "owner":
            raise AccessError("Only the workspace owner can make someone an admin.")
        m.role = role
    if instance_ids != "keep":
        m.instance_ids = _clean_instance_ids(ctx, instance_ids)  # type: ignore[arg-type]
        if m.instance_ids is not None and m.selected_instance_id not in m.instance_ids:
            m.selected_instance_id = None
    if status is not None:
        if status not in ("active", "disabled"):
            raise AccessError("Status must be active or disabled.")
        if status == "active" and m.status == "disabled":
            check_member_room(ctx.db, ctx.workspace.id)
        m.status = status
    ctx.db.commit()
    return m


def remove_member(ctx: Ctx, member_id: str) -> None:
    ctx.require("manage_members")
    m = _member(ctx, member_id)
    if m.role == "owner":
        raise AccessError("The workspace owner can't be removed.")
    if m.user_id == ctx.user.id:
        raise AccessError("You can't remove yourself. Ask another admin.")
    if m.role == "admin" and ctx.role != "owner":
        raise AccessError("Only the workspace owner can remove an admin.")
    m.status = "removed"
    ctx.db.commit()


def forget_instance(db: Session, instance_id: str) -> None:
    """An instance was removed: drop it from members' access lists and selections."""
    for m in db.scalars(select(Membership).where(Membership.selected_instance_id == instance_id)):
        m.selected_instance_id = None
    for m in db.scalars(select(Membership).where(Membership.instance_ids.is_not(None))):
        if instance_id in (m.instance_ids or []):
            m.instance_ids = [o for o in m.instance_ids if o != instance_id]
    for i in db.scalars(select(Invite).where(Invite.instance_ids.is_not(None))):
        if instance_id in (i.instance_ids or []):
            i.instance_ids = [o for o in i.instance_ids if o != instance_id]
