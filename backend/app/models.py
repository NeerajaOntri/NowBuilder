import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Set when the person typed the code we emailed them (or reset their password from an email link)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # In every session token; a password reset adds 1, which signs out every earlier session
    session_version: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)

    instances: Mapped[list["Instance"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def email_verified(self) -> bool:
        from .config import get_settings
        return self.email_verified_at is not None or not get_settings().require_email_verification

    @property
    def is_platform_admin(self) -> bool:
        """Platform admin: listed in NOWBUILDER_PLATFORM_ADMINS (the first admin, set on the server) or
        added on the Platform page (PlatformAdmin). Only once the email is confirmed, so nobody can
        claim an admin's address by signing up with it first."""
        from sqlalchemy import select
        from sqlalchemy.orm import object_session

        from .config import get_settings
        if not self.email_verified:
            return False
        email = self.email.strip().lower()
        if email in get_settings().platform_admin_emails:
            return True
        db = object_session(self)
        return bool(db and db.scalar(select(PlatformAdmin.id).where(PlatformAdmin.email == email)))

    ai_provider: Mapped["AIProviderConfig | None"] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    """A one-time secret sent by email: a 6-digit sign-up code (purpose "verify") or a password
    reset link (purpose "reset"). Only a hash is stored."""

    __tablename__ = "auth_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))
    secret_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PlatformAdmin(Base):
    """A platform admin added on the Platform page (by email, so they can be added before they sign
    up). Admins from NOWBUILDER_PLATFORM_ADMINS aren't stored here and can't be removed in the app."""

    __tablename__ = "platform_admins"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    added_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Workspace(Base):
    """A team's shared space: its members, ServiceNow instances, AI provider, chats and plans."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(80))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Set by a platform admin (services/platform.py). status: active | pending (waiting for approval)
    # | suspended (turned off) | closed (left empty when its owner joined another workspace).
    status: Mapped[str] = mapped_column(String(16), default="active")
    plan: Mapped[str | None] = mapped_column(String(32), nullable=True)  # None = the standard plan
    max_instances: Mapped[int | None] = mapped_column(Integer, nullable=True)  # override of the plan's limit
    max_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    platform_note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Membership(Base):
    """A user's place in a workspace. One active membership per user (one workspace per person).
    `instance_ids` None = every instance in the workspace; otherwise only those instances."""

    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # owner | admin | developer | reviewer | viewer
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | disabled | removed | left
    instance_ids: Mapped[list | None] = mapped_column(JSON)
    selected_instance_id: Mapped[str | None] = mapped_column(String(32))
    invited_by: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Invite(Base):
    """An invitation link. Only a hash of the token is stored; the link is shown once."""

    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(String(20))
    instance_ids: Mapped[list | None] = mapped_column(JSON)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | accepted | revoked
    created_by: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Instance(Base):
    """A ServiceNow instance connected to a workspace. Secrets are stored encrypted, never returned."""

    __tablename__ = "instances"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_instance_name_per_workspace"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)  # who connected it
    workspace_id: Mapped[str | None] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(80))
    instance_type: Mapped[str] = mapped_column(String(20))  # Development | Test | Production
    url: Mapped[str] = mapped_column(String(255))            # https://<name>.service-now.com
    # How nowBuilder signs in: basic (username + password) | oauth (OAuth password grant with an
    # Application Registry client id/secret; access tokens renewed with the refresh token)
    auth_method: Mapped[str] = mapped_column(String(20), default="basic")
    username: Mapped[str] = mapped_column(String(255))
    password_enc: Mapped[str] = mapped_column(Text, default="")
    client_id: Mapped[str] = mapped_column(String(255), default="")
    client_secret_enc: Mapped[str] = mapped_column(Text, default="")
    access_token_enc: Mapped[str] = mapped_column(Text, default="")
    refresh_token_enc: Mapped[str] = mapped_column(Text, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Read from the instance when the connection is checked
    release: Mapped[str | None] = mapped_column(String(120))        # e.g. "Xanadu" build name
    user_sys_id: Mapped[str | None] = mapped_column(String(32))
    user_display_name: Mapped[str | None] = mapped_column(String(255))
    roles: Mapped[list | None] = mapped_column(JSON)               # roles of the connected user
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Deploy plans straight after they are written and checked (never on Production)
    auto_deploy: Mapped[bool] = mapped_column(Boolean, default=True)

    status: Mapped[str] = mapped_column(String(20), default="connected")  # connected | error
    status_message: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="instances")


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)  # who started it
    workspace_id: Mapped[str | None] = mapped_column(String(32), index=True)
    instance_id: Mapped[str | None] = mapped_column(ForeignKey("instances.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(120), default="New chat")
    jira_key: Mapped[str | None] = mapped_column(String(40), index=True)  # Jira story this chat was built from
    jira: Mapped[dict | None] = mapped_column(JSON)  # {key, summary, url, type, pending_attachments?}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list["Message"]] = relationship(back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12))  # user | assistant
    content: Mapped[str] = mapped_column(Text, default="")
    attachments: Mapped[list] = mapped_column(JSON, default=list)  # [{name, size, chars}]
    attachment_text: Mapped[str] = mapped_column(Text, default="")  # extracted text sent to the AI
    activity: Mapped[list] = mapped_column(JSON, default=list)  # progress lines shown while working
    plan_id: Mapped[str | None] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    chat: Mapped[Chat] = relationship(back_populates="messages")


class Plan(Base):
    """An implementation plan shown as a card in the chat. Change requests create a new version."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    instance_id: Mapped[str | None] = mapped_column(String(32))
    parent_plan_id: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(default=1)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text)
    story_points: Mapped[int] = mapped_column(default=0)
    assumptions: Mapped[list] = mapped_column(JSON, default=list)
    components: Mapped[list] = mapped_column(JSON, default=list)
    application: Mapped[str | None] = mapped_column(String(80))  # scope every artifact is built in: global or x_…
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved | deployed
    busy: Mapped[str | None] = mapped_column(String(20))  # building | validating | fixing | deploying while an operation runs
    busy_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress: Mapped[str | None] = mapped_column(String(300))  # latest progress line of a background build
    validation: Mapped[dict | None] = mapped_column(JSON)  # {status, at, message, errors, deploy_id}
    approval: Mapped[dict | None] = mapped_column(JSON)  # {at, ids}: what Approve Plan locked in for Deploy
    deployment: Mapped[dict | None] = mapped_column(JSON)  # last deploy: {status, at, ids, update_set, message}
    git: Mapped[dict | None] = mapped_column(JSON)  # last Push to Git: {repo, branch, base, commit, pr_number, pr_url, pr_state, at, by, ids}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FixProposal(Base):
    """A Fix with AI result waiting for the user (Apply / Reject), or a record of a past attempt."""

    __tablename__ = "fix_proposals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[str] = mapped_column(String(16))
    group_ids: Mapped[list] = mapped_column(JSON, default=list)
    prior_statuses: Mapped[dict] = mapped_column(JSON, default=dict)  # restored on reject
    status: Mapped[str] = mapped_column(String(20))  # pending | applied | rejected | needs_user_input | blocked | failed
    summary: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str | None] = mapped_column(String(10))
    question: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[list] = mapped_column(JSON, default=list)       # [{id, reason, files:[{path, content}]}]
    new_components: Mapped[list] = mapped_column(JSON, default=list)
    original_files: Mapped[dict] = mapped_column(JSON, default=dict)  # path → content before the fix (for diffs)
    violations: Mapped[list] = mapped_column(JSON, default=list)
    attempt: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)  # who saved it
    workspace_id: Mapped[str | None] = mapped_column(String(32), index=True)  # shared by the whole workspace
    provider: Mapped[str] = mapped_column(String(40), default="anthropic")
    model: Mapped[str] = mapped_column(String(120))
    api_key_enc: Mapped[str] = mapped_column(Text)
    api_key_last4: Mapped[str] = mapped_column(String(4))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_message: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    # 26 Oct 2026: any provider. provider = what the admin typed (a known name like "openai" is
    # normalised); base_url for OpenAI-compatible services; prices in US$ per million tokens (for
    # the usage view's cost estimate); limits read from the provider when the key was verified.
    provider_name: Mapped[str | None] = mapped_column(String(80))  # what the admin typed, shown back as is
    base_url: Mapped[str | None] = mapped_column(String(300))
    price_input: Mapped[float | None] = mapped_column(Float)
    price_output: Mapped[float | None] = mapped_column(Float)
    model_info: Mapped[dict | None] = mapped_column(JSON)    # {context, max_output, display_name, source}
    rate_limits: Mapped[dict | None] = mapped_column(JSON)   # {requests_per_minute, input_tokens_per_minute, …}

    user: Mapped[User] = relationship(back_populates="ai_provider")


class AIUsage(Base):
    """One AI call: who, what for, which model, tokens and the estimated cost at that time's prices."""

    __tablename__ = "ai_usage"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workspace_id: Mapped[str | None] = mapped_column(String(32), index=True)
    user_id: Mapped[str | None] = mapped_column(String(32), index=True)
    operation: Mapped[str] = mapped_column(String(40))   # chat | generate | fix | auto_repair
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120))
    chat_id: Mapped[str | None] = mapped_column(String(32))
    plan_id: Mapped[str | None] = mapped_column(String(32))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float)  # not used any more (credits replaced money, 26 Oct)
    credits: Mapped[float | None] = mapped_column(Float)   # providers.credits_for(usage) at the time of the call
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class Integration(Base):
    """A workspace's connection to Jira or GitHub. One per kind per workspace. The token
    is stored encrypted and never returned; `config` holds the non-secret settings."""

    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("workspace_id", "kind", name="uq_integration_kind_per_workspace"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # jira | github
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    token_enc: Mapped[str] = mapped_column(Text, default="")
    token_last4: Mapped[str] = mapped_column(String(4), default="")

    status: Mapped[str] = mapped_column(String(20), default="connected")  # connected | error
    status_message: Mapped[str | None] = mapped_column(Text)
    connected_by: Mapped[str | None] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
