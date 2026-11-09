"""Workspace connections to Jira and GitHub (Chunk 9): stored settings, clients, Jira comments."""
from __future__ import annotations

import logging
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Integration
from ..security import SecretUnreadable, decrypt
from .github import GitHubClient
from .jira import JiraClient

log = logging.getLogger("nowbuilder")
KINDS = ("jira", "github")


def get(db: Session, workspace_id: str, kind: str) -> Integration | None:
    return db.scalar(select(Integration).where(Integration.workspace_id == workspace_id, Integration.kind == kind))


def _make_jira(integ: Integration) -> JiraClient:
    c = integ.config or {}
    return JiraClient(c["site"], c["email"], decrypt(integ.token_enc))


def _make_github(integ: Integration) -> GitHubClient:
    return GitHubClient(decrypt(integ.token_enc))


# Swappable in tests and the local fake server
make_jira = _make_jira
make_github = _make_github


def jira_client(integ: Integration) -> JiraClient:
    return make_jira(integ)


def github_client(integ: Integration) -> GitHubClient:
    return make_github(integ)


def out(integ: Integration | None, kind: str, org_names: dict[str, str] | None = None) -> dict:
    """What the browser sees: settings and status, never the token."""
    if integ is None:
        return {"kind": kind, "connected": False}
    c = dict(integ.config or {})
    d = {"kind": kind, "connected": True, "status": integ.status, "status_message": integ.status_message,
         "token_masked": f"••••••••{integ.token_last4}" if integ.token_last4 else None, "updated_at": integ.updated_at.isoformat()}
    if kind == "jira":
        d.update(site=c.get("site"), email=c.get("email"), account=c.get("account"), projects=c.get("projects") or [],
                 comments=c.get("comments", True))
    else:
        names = org_names or {}
        d.update(login=c.get("login"), repos={k: v for k, v in (c.get("repos") or {}).items() if k in names} if org_names is not None else c.get("repos") or {})
    return d


# ---------- comments on Jira stories (best effort, never blocks the work) ----------

def comment_on_story(workspace_id: str, key: str | None, text: str, link: tuple[str, str] | None = None, wait: bool = False) -> None:
    if not key:
        return

    def run() -> None:
        from ..db import SessionLocal
        db = SessionLocal()
        try:
            integ = get(db, workspace_id, "jira")
            if integ is None or integ.status != "connected" or not (integ.config or {}).get("comments", True):
                return
            client = jira_client(integ)
            try:
                client.comment(key, text, link)
            finally:
                client.close()
        except SecretUnreadable:
            log.warning("Jira comment on %s skipped: the saved token can't be read", key)
        except Exception as e:  # noqa: BLE001  (a comment must never break a deploy or a plan)
            log.warning("Jira comment on %s failed: %s", key, e)
        finally:
            db.close()

    if wait:
        run()
    else:
        threading.Thread(target=run, daemon=True, name=f"jira-comment-{key}").start()


# Tests set this to True so comments run before the request returns
COMMENTS_WAIT = False


def comment(workspace_id: str, key: str | None, text: str, link: tuple[str, str] | None = None) -> None:
    comment_on_story(workspace_id, key, text, link, wait=COMMENTS_WAIT)
