"""Chunk 9: Jira and GitHub.

- Settings → Jira / Settings → GitHub: connect Jira (site, email, API token, projects) and GitHub (token, a repo
  and base branch per ServiceNow instance). Tokens are encrypted and never returned.
- Jira stories: list (assigned to me / all in the projects, open / all, search), details, Build
  (a chat linked to the story, whose first message is the story).
- Push to Git: an approved or deployed plan's files go to a branch and a pull request.
"""
from __future__ import annotations

import copy
import re
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..deps import DB, WorkspaceCtx
from ..models import Chat, Integration
from ..security import SecretUnreadable, decrypt, encrypt
from ..services import integrations as integ_svc
from ..services.attachments import SUPPORTED, AttachmentError, extract_text
from ..services.github import GitHubError, branch_name, valid_branch
from ..services.jira import MAX_ATTACHMENT_BYTES, MAX_ATTACHMENTS, JiraError, build_jql, cached_account, clean_site, requirement
from ..services.workspace import Ctx
from .chats import chat_out

router = APIRouter(prefix="/api", tags=["integrations"])
KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,30}-\d{1,9}$")


def _bad(e: Exception, code: int = status.HTTP_400_BAD_REQUEST) -> HTTPException:
    return HTTPException(code, str(e))


def _integ(ctx: Ctx, kind: str, required: bool = True) -> Integration | None:
    i = integ_svc.get(ctx.db, ctx.workspace.id, kind)
    if i is None and required:
        where = "Settings → Jira" if kind == "jira" else "Settings → GitHub"
        who = f"Connect it in {where}." if ctx.can("manage_integrations") else f"Ask a workspace admin to connect it in {where}."
        raise HTTPException(status.HTTP_409_CONFLICT, f"{'Jira' if kind == 'jira' else 'GitHub'} isn't connected yet. {who}")
    return i


def _client(kind: str, integ: Integration):
    try:
        return integ_svc.jira_client(integ) if kind == "jira" else integ_svc.github_client(integ)
    except SecretUnreadable as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    except JiraError as e:
        raise _bad(e) from e


def _instance_names(ctx: Ctx) -> dict[str, str]:
    return {o.id: o.name for o in ctx.all_instances()}


# ---------- Settings → Jira / GitHub ----------

@router.get("/integrations")
def get_integrations(ctx: WorkspaceCtx) -> dict:
    names = _instance_names(ctx)
    return {"jira": integ_svc.out(_integ(ctx, "jira", False), "jira"),
            "github": integ_svc.out(_integ(ctx, "github", False), "github", names),
            "can_manage": ctx.can("manage_integrations"),
            "instances": [{"id": o.id, "name": o.name, "instance_type": o.instance_type} for o in ctx.all_instances()]}


class JiraIn(BaseModel):
    site: str = Field(min_length=3, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    token: str | None = Field(default=None, max_length=1000)
    projects: list[str] | None = None
    comments: bool = True


def _save(ctx: Ctx, kind: str, integ: Integration | None, token: str, config: dict) -> Integration:
    db = ctx.db
    if integ is None:
        integ = Integration(workspace_id=ctx.workspace.id, kind=kind)
        db.add(integ)
    integ.config, integ.token_enc, integ.token_last4 = config, encrypt(token), token[-4:]
    integ.status, integ.status_message, integ.connected_by = "connected", None, ctx.user.id
    integ.updated_at = datetime.now(UTC)
    db.commit()
    return integ


def _token(body_token: str | None, integ: Integration | None, label: str) -> str:
    if body_token and body_token.strip():
        return body_token.strip()
    if integ is not None:
        try:
            return decrypt(integ.token_enc)
        except SecretUnreadable as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Enter the {label} again: the saved one can't be read.") from e
    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Enter the {label}.")


@router.put("/integrations/jira")
def save_jira(body: JiraIn, ctx: WorkspaceCtx) -> dict:
    ctx.require("manage_integrations")
    integ = _integ(ctx, "jira", False)
    try:
        site = clean_site(body.site)
    except JiraError as e:
        raise _bad(e) from e
    if integ is not None and (integ.config or {}).get("site") != site and not (body.token or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter the API token again for the new site.")
    token = _token(body.token, integ, "API token")
    probe = Integration(workspace_id=ctx.workspace.id, kind="jira", config={"site": site, "email": body.email.strip()}, token_enc=encrypt(token))
    client = _client("jira", probe)
    try:
        me = client.myself()
        known = {p["key"] for p in client.projects()}
    except JiraError as e:
        raise _bad(e) from e
    finally:
        client.close()
    projects = [p.strip().upper() for p in (body.projects or []) if p.strip()]
    if unknown := [p for p in projects if p not in known]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"nowBuilder's Jira account can't see space {', '.join(unknown)}. Check the key (like SCRUM in SCRUM-21).")
    from ..services.jira import forget_accounts
    forget_accounts()
    integ = _save(ctx, "jira", integ, token, {"site": site, "email": body.email.strip(), "account": me.get("name"),
                                              "projects": projects, "comments": body.comments})
    return integ_svc.out(integ, "jira")


@router.get("/integrations/jira/projects")
def jira_projects(ctx: WorkspaceCtx) -> list[dict]:
    ctx.require("manage_integrations")
    client = _client("jira", _integ(ctx, "jira"))
    try:
        return client.projects()
    except JiraError as e:
        raise _bad(e, status.HTTP_502_BAD_GATEWAY) from e
    finally:
        client.close()


class RepoIn(BaseModel):
    repo: str = Field(max_length=200)
    branch: str = Field(max_length=200)


class GitHubIn(BaseModel):
    token: str | None = Field(default=None, max_length=1000)
    repos: dict[str, RepoIn | None] | None = None


@router.put("/integrations/github")
def save_github(body: GitHubIn, ctx: WorkspaceCtx) -> dict:
    ctx.require("manage_integrations")
    integ = _integ(ctx, "github", False)
    token = _token(body.token, integ, "access token")
    probe = Integration(workspace_id=ctx.workspace.id, kind="github", config={}, token_enc=encrypt(token))
    client = _client("github", probe)
    names = _instance_names(ctx)
    repos = dict((integ.config or {}).get("repos") or {}) if integ else {}
    try:
        user = client.user()
        if body.repos is not None:
            for instance_id, r in body.repos.items():
                if instance_id not in names:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "That ServiceNow instance isn't in this workspace.")
                if r is None or not r.repo.strip():
                    repos.pop(instance_id, None)
                    continue
                repo, branch = r.repo.strip(), r.branch.strip()
                if not valid_branch(branch):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Choose a base branch for {names[instance_id]}.")
                if branch not in client.branches(repo):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"The branch {branch} doesn't exist in {repo}.")
                repos[instance_id] = {"repo": repo, "branch": branch}
    except GitHubError as e:
        raise _bad(e) from e
    finally:
        client.close()
    integ = _save(ctx, "github", integ, token, {"login": user.get("login"), "repos": repos})
    return integ_svc.out(integ, "github", names)


@router.get("/integrations/github/repos")
def github_repos(ctx: WorkspaceCtx) -> list[dict]:
    ctx.require("manage_integrations")
    client = _client("github", _integ(ctx, "github"))
    try:
        return client.repos()
    except GitHubError as e:
        raise _bad(e, status.HTTP_502_BAD_GATEWAY) from e
    finally:
        client.close()


@router.get("/integrations/github/branches")
def github_branches(repo: str, ctx: WorkspaceCtx) -> list[str]:
    ctx.require("manage_integrations")
    client = _client("github", _integ(ctx, "github"))
    try:
        return client.branches(repo)
    except GitHubError as e:
        raise _bad(e, status.HTTP_502_BAD_GATEWAY) from e
    finally:
        client.close()


@router.delete("/integrations/{kind}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(kind: str, ctx: WorkspaceCtx) -> None:
    ctx.require("manage_integrations")
    if kind not in integ_svc.KINDS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    integ = _integ(ctx, kind, False)
    if integ:
        ctx.db.delete(integ)
        ctx.db.commit()


# ---------- Jira stories ----------

def _story_chats(ctx: Ctx) -> dict[str, str]:
    """Story key → the newest chat built from it that this member can see."""
    out: dict[str, str] = {}
    for c in ctx.db.scalars(select(Chat).where(Chat.workspace_id == ctx.workspace.id, Chat.jira_key.is_not(None)).order_by(Chat.updated_at)):
        if ctx.can_see_chat(c):
            out[c.jira_key] = c.id
    return out


def _check_key(key: str) -> str:
    key = key.strip().upper()
    if not KEY_RE.match(key):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That isn't a Jira issue key (like SCRUM-21).")
    return key


@router.get("/jira/stories")
def list_stories(ctx: WorkspaceCtx, scope: str = "mine", open: bool = True, q: str | None = None) -> dict:  # noqa: A002
    integ = _integ(ctx, "jira")
    cfg = integ.config or {}
    client = _client("jira", integ)
    note = None
    try:
        account = None
        if scope == "mine":
            account = cached_account(cfg["site"], ctx.user.email, lambda: client.account_for_email(ctx.user.email))
            if account is None:
                scope, note = "all", (f"Jira has no user with your email ({ctx.user.email}) that nowBuilder can see, "
                                      "so these are all the stories in the chosen Jira spaces.")
        stories = client.search(build_jql(cfg.get("projects") or [], account, open, (q or "")[:200]), limit=100)
    except JiraError as e:
        raise _bad(e, status.HTTP_502_BAD_GATEWAY) from e
    finally:
        client.close()
    chats = _story_chats(ctx)
    return {"scope": scope, "note": note, "site": cfg.get("site"), "projects": cfg.get("projects") or [],
            "stories": [{**s.out(), "chat_id": chats.get(s.key)} for s in stories]}


@router.get("/jira/stories/{key}")
def get_story(key: str, ctx: WorkspaceCtx) -> dict:
    key = _check_key(key)
    client = _client("jira", _integ(ctx, "jira"))
    try:
        story, extra = client.story(key)
    except JiraError as e:
        raise _bad(e, status.HTTP_502_BAD_GATEWAY) from e
    finally:
        client.close()
    atts = [{"name": a["name"], "size": a["size"], "readable": (a["name"] or "").lower().endswith(SUPPORTED) and a["size"] <= MAX_ATTACHMENT_BYTES}
            for a in extra["attachments"]]
    return {**story.out(preview=None), "acceptance": extra["acceptance"], "labels": extra["labels"], "subtasks": extra["subtasks"],
            "components": extra["components"], "attachments": atts, "chat_id": _story_chats(ctx).get(key)}


class BuildIn(BaseModel):
    instance_id: str | None = None
    again: bool = False  # start a new chat even if one exists


@router.post("/jira/stories/{key}/build")
def build_story(key: str, body: BuildIn, ctx: WorkspaceCtx, db: DB) -> dict:
    """A chat linked to the story. The browser sends `requirement` as its first message (with
    story=true, so the story's readable attachments go with it)."""
    key = _check_key(key)
    ctx.require("build")
    existing = _story_chats(ctx).get(key)
    if existing and not body.again:
        return {"chat": chat_out(db.get(Chat, existing), ctx.user), "existing": True, "requirement": None}
    inst = ctx.instance(body.instance_id) if body.instance_id else ctx.selected_instance()
    if body.instance_id and inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instance not found.")
    client = _client("jira", _integ(ctx, "jira"))
    files, skipped = [], []
    try:
        story, extra = client.story(key)
        for a in extra["attachments"]:
            name = a["name"] or "attachment"
            if len(files) >= MAX_ATTACHMENTS or not name.lower().endswith(SUPPORTED) or a["size"] > MAX_ATTACHMENT_BYTES or not a["url"]:
                skipped.append(name)
                continue
            try:
                text = extract_text(name, client.download(a["url"]))
                files.append({"name": name, "size": a["size"], "chars": len(text), "text": text})
            except (AttachmentError, JiraError):
                skipped.append(name)
    except JiraError as e:
        raise _bad(e, status.HTTP_502_BAD_GATEWAY) from e
    finally:
        client.close()
    chat = Chat(user_id=ctx.user.id, workspace_id=ctx.workspace.id, instance_id=inst.id if inst else None,
                title=f"{story.key}: {story.summary}"[:120], jira_key=story.key,
                jira={"key": story.key, "summary": story.summary, "url": story.url, "type": story.type, "status": story.status,
                      "pending_attachments": files})
    db.add(chat)
    db.commit()
    return {"chat": chat_out(chat, ctx.user), "existing": False, "requirement": requirement(story, extra),
            "attachments": [f["name"] for f in files], "skipped_attachments": skipped}


# ---------- Push to Git ----------


# Push to Git (a plan's records as files on a branch + pull request) comes back with Chunk 4 (deploy).
