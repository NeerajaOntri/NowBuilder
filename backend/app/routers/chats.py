import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..ai.chat_engine import ChatContext, ChatTurn
from ..ai.planning import PlanBuilder
from ..ai.tools import ToolRunner
from ..ai import usage
from ..ai.llm import AnthropicLLM, LLM, build_llm  # noqa: F401  (AnthropicLLM kept for imports elsewhere)
from ..ai.skills import get_skills
from ..db import SessionLocal
from ..deps import DB, WorkspaceCtx
from ..models import AIProviderConfig, Chat, Message, Plan, Instance, User
from ..services.workspace import AccessError, Ctx
from ..security import decrypt
from ..services.attachments import AttachmentError, extract_text
from ..services.servicenow import ServiceNowClient
from .plans import plans_for_chat

router = APIRouter(prefix="/api", tags=["chat"])
MAX_HISTORY_MESSAGES = 24


# ---------- serialisation ----------

def message_out(m: Message) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "attachments": m.attachments, "activity": m.activity,
            "plan_id": m.plan_id, "error": m.error, "created_at": m.created_at.isoformat()}


def chat_out(c: Chat, owner: User | None = None) -> dict:
    return {"id": c.id, "title": c.title, "instance_id": c.instance_id, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat(),
            "user_id": c.user_id, "by": f"{owner.first_name} {owner.last_name}".strip() if owner else None,
            "jira": {k: v for k, v in c.jira.items() if k != "pending_attachments"} if c.jira else None}


def _get_chat(ctx: Ctx, chat_id: str, action: str = "read") -> Chat:
    chat = ctx.db.get(Chat, chat_id)
    if not ctx.can_see_chat(chat):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found.")
    ctx.require(action)
    return chat


# ---------- chats ----------

class ChatRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@router.get("/chats")
def list_chats(ctx: WorkspaceCtx, db: DB) -> list[dict]:
    """The workspace's chats for the instances this member can use (a shared team space)."""
    chats = [c for c in db.scalars(select(Chat).where(Chat.workspace_id == ctx.workspace.id).order_by(Chat.updated_at.desc()).limit(400))
             if ctx.can_see_chat(c)][:200]
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_({c.user_id for c in chats} or {""})))}
    return [chat_out(c, users.get(c.user_id)) for c in chats]


@router.post("/chats", status_code=status.HTTP_201_CREATED)
def create_chat(ctx: WorkspaceCtx, db: DB) -> dict:
    ctx.require("build")
    inst = ctx.selected_instance()
    chat = Chat(user_id=ctx.user.id, workspace_id=ctx.workspace.id, instance_id=inst.id if inst else None)
    db.add(chat)
    db.commit()
    return chat_out(chat, ctx.user)


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str, ctx: WorkspaceCtx, db: DB) -> dict:
    chat = _get_chat(ctx, chat_id)
    return {**chat_out(chat, db.get(User, chat.user_id)), "messages": [message_out(m) for m in chat.messages],
            "plans": plans_for_chat(db, chat)}


def _own_or_admin(ctx: Ctx, chat: Chat) -> None:
    if chat.user_id != ctx.user.id and not ctx.can("manage_members"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the person who started this chat, or a workspace admin, can rename or delete it.")


@router.patch("/chats/{chat_id}")
def rename_chat(chat_id: str, body: ChatRename, ctx: WorkspaceCtx, db: DB) -> dict:
    chat = _get_chat(ctx, chat_id, "build")
    _own_or_admin(ctx, chat)
    chat.title = body.title.strip()
    db.commit()
    return chat_out(chat, db.get(User, chat.user_id))


@router.delete("/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: str, ctx: WorkspaceCtx, db: DB) -> None:
    chat = _get_chat(ctx, chat_id, "build")
    _own_or_admin(ctx, chat)
    for p in db.scalars(select(Plan).where(Plan.chat_id == chat.id)):
        db.delete(p)
    db.delete(chat)
    db.commit()


# ---------- conversation history and context ----------

def build_history(db, chat: Chat) -> list[dict]:
    out: list[dict] = []
    for m in chat.messages[-MAX_HISTORY_MESSAGES:]:
        if m.role == "user":
            text = m.content
            if m.attachment_text:
                names = ", ".join(a["name"] for a in m.attachments) or "attachment"
                text += f"\n\n<attached_document name=\"{names}\">\n{m.attachment_text}\n</attached_document>"
        else:
            text = m.content or ("(Error: " + m.error + ")" if m.error else "")
        text = text.strip() or "(no reply)"
        if out and out[-1]["role"] == m.role:
            out[-1]["content"] += "\n\n" + text
        else:
            out.append({"role": m.role, "content": text})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def _release_plan(db, plan_id: str | None) -> None:
    """A plan left mid-build (the browser closed) isn't busy any more; its rows keep their status."""
    plan = db.get(Plan, plan_id) if plan_id else None
    if plan is not None and plan.busy:
        plan.busy = None
        plan.busy_since = None
        plan.progress = None
        for c in plan.components or []:
            if c.get("status") == "generating":
                c["status"] = "failed"
                c["error"] = "Stopped before this artifact was written."
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(plan, "components")
        db.commit()


def _requirement(history: list[dict]) -> str:
    """What the user asked for, for the generation prompts (their messages, newest last)."""
    return "\n\n".join(m["content"] for m in history[-6:] if m["role"] == "user" and isinstance(m["content"], str))[-6000:]


def instance_summary(inst: Instance) -> str:
    who = inst.user_display_name or inst.username or "unknown user"
    roles = ", ".join((inst.roles or [])[:15]) or "unknown"
    return (f"{inst.name}: {inst.instance_type} instance at {inst.url}, release {inst.release or 'unknown'}. "
            f"Signed in as {who} (roles: {roles}{'' if inst.is_admin else '; not admin, some sys_ tables may be unreadable'}). "
            f"Status: {inst.status}.")


def current_application(inst: Instance, client) -> str:
    """The user's current application in the instance (the application picker), so the assistant can
    offer it when asking where to build. Best effort: unreadable means not mentioned."""
    try:
        if not inst.user_sys_id:
            return ""
        rows = client.query("sys_user_preference", f"name=apps.current_app^user={inst.user_sys_id}", ["value"], limit=1)
        value = str((rows[0] if rows else {}).get("value") or "")
        if not value or value == "global":
            return " Current application in the instance: Global."
        scope = client.get("sys_scope", value, fields=["name", "scope"]) or {}
        return f" Current application in the instance: {scope.get('name') or value} ({scope.get('scope') or 'scoped'})."
    except Exception:  # noqa: BLE001 - only context for the assistant
        return ""


# The model factory can be swapped in tests
def make_llm(cfg: AIProviderConfig) -> LLM:
    """The workspace's AI provider (one shared key per workspace): Anthropic or any OpenAI-compatible service."""
    return build_llm(cfg.provider or "anthropic", decrypt(cfg.api_key_enc), cfg.model, cfg.base_url)


llm_factory = make_llm


# ---------- send a message (streams Server-Sent Events) ----------

def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: str, ctx: WorkspaceCtx, db: DB,
    text: Annotated[str, Form(max_length=20_000)] = "",
    files: Annotated[list[UploadFile] | None, File()] = None,
    story: Annotated[bool, Form()] = False,
) -> StreamingResponse:
    chat = _get_chat(ctx, chat_id, "build")
    ai_cfg = ctx.ai_config()
    if not ai_cfg or not ai_cfg.verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add and verify the workspace's AI provider in Settings → AI provider first.")

    attachments, attachment_text = [], []
    for f in (files or [])[:3]:
        data = await f.read()
        try:
            extracted = extract_text(f.filename or "attachment", data)
        except AttachmentError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
        attachments.append({"name": f.filename, "size": len(data), "chars": len(extracted)})
        attachment_text.append(f"--- {f.filename} ---\n{extracted}" if len(files or []) > 1 else extracted)
    if story and chat.jira and chat.jira.get("pending_attachments"):  # first message of a chat built from a Jira story
        pending = chat.jira["pending_attachments"]
        for a in pending:
            attachments.append({"name": a["name"], "size": a["size"], "chars": a["chars"], "from": "jira"})
            attachment_text.append(f"--- {a['name']} (attached to {chat.jira['key']}) ---\n{a['text']}")
        chat.jira = {k: v for k, v in chat.jira.items() if k != "pending_attachments"}
    if not text.strip() and not attachments:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type a message or attach a document.")

    user_msg = Message(chat_id=chat.id, role="user", content=text.strip(), attachments=attachments, attachment_text="\n\n".join(attachment_text))
    db.add(user_msg)
    if chat.title == "New chat":
        chat.title = (text.strip() or f'Requirement from {attachments[0]["name"]}')[:80]
    chat.updated_at = datetime.now(UTC)
    # A chat works in the instance that is in use now (the switcher at the top), so switching
    # instances never leaves a chat reading or deploying to the previous one.
    inst = ctx.instance(chat.instance_id)
    selected = ctx.selected_instance()
    if selected is not None and (inst is None or inst.id != selected.id):
        inst = selected
        chat.instance_id = selected.id
    elif inst is None and chat.instance_id is not None and db.get(Instance, chat.instance_id) is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to this chat's instance.")
    db.commit()

    llm = usage.metered(llm_factory(ai_cfg), ai_cfg, user_id=ctx.user.id, operation="chat", chat_id=chat.id)
    chat_id, user_msg_id, instance_id = chat.id, user_msg.id, (inst.id if inst else None)
    from ..services import auto_deploy
    try:
        ctx.require_deploy(inst)
        can_deploy = True
    except AccessError:
        can_deploy = False
    may_deploy, no_deploy_reason = auto_deploy.allowed(inst, can_deploy)
    user_id = ctx.user.id

    def stream() -> Iterator[str]:
        # Own session: the request's session closes before streaming finishes
        sdb = SessionLocal()
        try:
            chat_s = sdb.get(Chat, chat_id)
            inst_s = sdb.get(Instance, instance_id) if instance_id else None
            summary = instance_summary(inst_s) if inst_s else None
            client = ServiceNowClient(inst_s, sdb) if inst_s else None
            if summary and client is not None:
                summary += current_application(inst_s, client)
            ctx = ChatContext(instance_summary=summary)
            skills = get_skills()
            history = build_history(sdb, chat_s)
            deployer = (auto_deploy.AutoDeployer(sdb, client, inst_s, user_id, llm=llm, skills=skills,
                                                 instance_summary=summary)
                        if may_deploy and inst_s is not None and client is not None else None)
            planner = PlanBuilder(llm, skills, ToolRunner(skills, client), sdb, chat_id, instance_id, summary,
                                  requirement=_requirement(history), client=client,
                                  deployer=deployer, no_deploy_reason=no_deploy_reason)
            turn = ChatTurn(llm, skills, client, ctx, history, planner)
            yield _sse({"type": "start", "user_message_id": user_msg_id})

            def save_reply() -> Message:
                r = turn.result
                msg = Message(chat_id=chat_id, role="assistant", content=r.text.strip(), activity=r.activity, plan_id=r.plan_id, error=r.error)
                sdb.add(msg)
                chat_s.updated_at = datetime.now(UTC)
                sdb.commit()
                return msg

            try:
                for event in turn.run():
                    yield _sse(event)
            except GeneratorExit:  # browser closed the stream: keep what we have
                if not turn.result.error:
                    turn.result.error = "Stopped before the reply finished."
                _release_plan(sdb, planner.plan_id)
                save_reply()
                raise
            yield _sse({"type": "done", "message": message_out(save_reply())})
        except Exception:  # noqa: BLE001
            yield _sse({"type": "error", "message": "nowBuilder hit an unexpected problem. Try again."})
            raise
        finally:
            sdb.close()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
