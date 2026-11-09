"""Jira Cloud (Chunk 9): read stories to build from, and comment on them as work progresses.

Connected once per workspace with an Atlassian account email + API token (Basic auth). Only
`https://` sites are accepted. Stories are read with the REST API v3 (`/search/jql`); descriptions
come as Atlassian Document Format and are turned into plain text here.

"Assigned to me" means the Jira user whose email matches the nowBuilder member's email. If Jira
hides emails (privacy settings) the member sees the stories of the chosen projects instead.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

log = logging.getLogger("nowbuilder")
TIMEOUT = 20.0
LIST_FIELDS = ["summary", "status", "priority", "issuetype", "description", "updated", "assignee", "project", "parent"]
MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


class JiraError(Exception):
    """Shown to the user as is."""


def clean_site(site: str) -> str:
    site = (site or "").strip().rstrip("/")
    if site and "://" not in site:
        site = "https://" + site
    u = urlparse(site)
    if u.scheme != "https" or not u.hostname or " " in site:
        raise JiraError("Enter your Jira site address, like https://yourcompany.atlassian.net.")
    return f"https://{u.hostname}"


# ---------- Atlassian Document Format → text ----------

def adf_text(node: object) -> str:
    """Plain text from an ADF document (or a string, for older APIs). Lists keep their bullets,
    tables become `a | b` rows, so the AI still sees the structure."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node.strip()
    out: list[str] = []

    def walk(n: dict, prefix: str = "") -> str:
        t = n.get("type")
        kids = n.get("content") or []
        if t == "text":
            return n.get("text", "")
        if t == "hardBreak":
            return "\n"
        if t in ("mention", "emoji"):
            return (n.get("attrs") or {}).get("text", "")
        if t == "inlineCard":
            return (n.get("attrs") or {}).get("url", "")
        if t in ("bulletList", "orderedList"):
            lines = []
            for i, item in enumerate(kids, 1):
                mark = f"{i}." if t == "orderedList" else "-"
                body = "\n".join(walk(k, prefix + "  ") for k in item.get("content") or []).strip()
                lines.append(f"{prefix}{mark} {body}")
            return "\n".join(lines)
        if t == "table":
            rows = []
            for row in kids:
                rows.append(" | ".join(" ".join(walk(k) for k in (cell.get("content") or [])).strip() for cell in row.get("content") or []))
            return "\n".join(rows)
        if t == "heading":
            return "".join(walk(k) for k in kids)
        if t == "codeBlock":
            return "```\n" + "".join(walk(k) for k in kids) + "\n```"
        if t in ("paragraph", "listItem", "blockquote", "panel", "expand", "nestedExpand"):
            sep = "" if t == "paragraph" else "\n"
            return sep.join(walk(k, prefix) for k in kids)
        if t == "rule":
            return "---"
        return "".join(walk(k, prefix) for k in kids) if isinstance(kids, list) else ""

    if isinstance(node, dict):
        for block in node.get("content") or [node]:
            text = walk(block).strip()
            if text:
                out.append(text)
    return "\n\n".join(out).strip()


def adf_doc(text: str, link: tuple[str, str] | None = None) -> dict:
    """A short comment as ADF: one paragraph per line, optional link at the end."""
    paras = [{"type": "paragraph", "content": [{"type": "text", "text": line}]} for line in text.split("\n") if line.strip()]
    if link:
        paras.append({"type": "paragraph", "content": [{"type": "text", "text": link[0], "marks": [{"type": "link", "attrs": {"href": link[1]}}]}]})
    return {"type": "doc", "version": 1, "content": paras}


# ---------- client ----------

@dataclass
class Story:
    key: str
    summary: str
    status: str
    status_category: str  # new | indeterminate | done
    priority: str | None
    type: str
    description: str
    updated: str | None
    assignee: str | None
    project: str
    url: str
    parent: str | None = None

    def out(self, preview: int | None = 400) -> dict:
        d = self.__dict__.copy()
        if preview is not None and len(self.description) > preview:
            d["description"] = self.description[:preview].rstrip() + "…"
        return d


class JiraClient:
    def __init__(self, site: str, email: str, token: str, transport: httpx.BaseTransport | None = None):
        self.site = clean_site(site)
        self.http = httpx.Client(base_url=self.site, auth=(email.strip(), token.strip()), timeout=TIMEOUT, transport=transport,
                                 headers={"Accept": "application/json"}, follow_redirects=True)

    def close(self) -> None:
        self.http.close()

    def _call(self, method: str, path: str, **kw) -> dict | list:
        try:
            r = self.http.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise JiraError(f"Couldn't reach Jira at {self.site}. Check the site address and try again.") from e
        if r.status_code in (401, 403) and path.endswith("/myself"):
            raise JiraError("Jira didn't accept that email and API token. Create a token at id.atlassian.com → Security → API tokens.")
        if r.status_code == 401:
            raise JiraError("Jira didn't accept the saved API token. An admin can reconnect Jira in Settings → Jira.")
        if r.status_code == 403:
            raise JiraError("The Jira account used by nowBuilder doesn't have permission to do that.")
        if r.status_code == 404:
            raise JiraError("Jira couldn't find that. It may have been deleted or moved, or nowBuilder's Jira account can't see it.")
        if r.status_code == 429:
            raise JiraError("Jira is limiting requests right now. Try again in a minute.")
        if r.status_code >= 400:
            msgs = []
            try:
                body = r.json()
                msgs = list(body.get("errorMessages") or []) + list((body.get("errors") or {}).values())
            except ValueError:
                pass
            raise JiraError("Jira said: " + (" ".join(msgs) if msgs else f"error {r.status_code}."))
        return r.json() if r.content else {}

    # ----- account and projects -----
    def myself(self) -> dict:
        me = self._call("GET", "/rest/api/3/myself")
        return {"account_id": me.get("accountId"), "name": me.get("displayName"), "email": me.get("emailAddress")}

    def projects(self) -> list[dict]:
        out, start = [], 0
        while True:
            page = self._call("GET", "/rest/api/3/project/search", params={"startAt": start, "maxResults": 50, "orderBy": "name"})
            out += [{"key": p["key"], "name": p["name"]} for p in page.get("values", [])]
            if page.get("isLast", True) or not page.get("values"):
                return out
            start += len(page["values"])

    def account_for_email(self, email: str) -> str | None:
        users = self._call("GET", "/rest/api/3/user/search", params={"query": email, "maxResults": 10})
        for u in users if isinstance(users, list) else []:
            if (u.get("emailAddress") or "").lower() == email.lower() and u.get("accountType", "atlassian") == "atlassian":
                return u.get("accountId")
        exact = [u for u in users if isinstance(u, dict) and u.get("accountType", "atlassian") == "atlassian"] if isinstance(users, list) else []
        return exact[0]["accountId"] if len(exact) == 1 else None  # email hidden but only one match

    # ----- stories -----
    def _story(self, issue: dict) -> Story:
        f = issue.get("fields") or {}
        st = f.get("status") or {}
        return Story(
            key=issue["key"], summary=f.get("summary") or "", status=st.get("name") or "",
            status_category=(st.get("statusCategory") or {}).get("key") or "", priority=(f.get("priority") or {}).get("name"),
            type=(f.get("issuetype") or {}).get("name") or "", description=adf_text(f.get("description")),
            updated=f.get("updated"), assignee=(f.get("assignee") or {}).get("displayName"),
            project=(f.get("project") or {}).get("key") or issue["key"].split("-")[0], url=f"{self.site}/browse/{issue['key']}",
            parent=(f.get("parent") or {}).get("key"),
        )

    def search(self, jql: str, limit: int = 50) -> list[Story]:
        out: list[Story] = []
        token = None
        while len(out) < limit:
            body = {"jql": jql, "fields": LIST_FIELDS, "maxResults": min(50, limit - len(out))}
            if token:
                body["nextPageToken"] = token
            page = self._call("POST", "/rest/api/3/search/jql", json=body)
            out += [self._story(i) for i in page.get("issues", [])]
            token = page.get("nextPageToken")
            if not token or page.get("isLast") or not page.get("issues"):
                break
        return out

    def story(self, key: str) -> tuple[Story, dict]:
        """A story with everything the AI needs: description, acceptance criteria (any field whose
        name mentions it), labels, sub-tasks and attachment details."""
        issue = self._call("GET", f"/rest/api/3/issue/{key}", params={"fields": "*all", "expand": "names"})
        s = self._story(issue)
        f, names = issue.get("fields") or {}, issue.get("names") or {}
        extra: dict = {"acceptance": "", "labels": f.get("labels") or [], "subtasks": [], "attachments": [], "components": []}
        for fid, name in names.items():
            if re.search(r"acceptance|definition of done", name or "", re.I) and f.get(fid):
                extra["acceptance"] = adf_text(f[fid]) if not isinstance(f[fid], (int, float)) else str(f[fid])
                break
        extra["subtasks"] = [{"key": t["key"], "summary": (t.get("fields") or {}).get("summary", "")} for t in f.get("subtasks") or []]
        extra["components"] = [c.get("name") for c in f.get("components") or [] if c.get("name")]
        extra["attachments"] = [{"id": a.get("id"), "name": a.get("filename"), "size": a.get("size") or 0, "url": a.get("content"),
                                 "mime": a.get("mimeType")} for a in f.get("attachment") or []]
        return s, extra

    def download(self, url: str) -> bytes:
        if not url.startswith(self.site + "/"):
            raise JiraError("That attachment isn't on the connected Jira site.")
        try:
            r = self.http.get(url)
        except httpx.HTTPError as e:
            raise JiraError("Couldn't download the attachment from Jira.") from e
        if r.status_code >= 400:
            raise JiraError("Couldn't download the attachment from Jira.")
        return r.content

    def comment(self, key: str, text: str, link: tuple[str, str] | None = None) -> None:
        self._call("POST", f"/rest/api/3/issue/{key}/comment", json={"body": adf_doc(text, link)})


# ---------- JQL ----------

def _q(v: str) -> str:
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_jql(projects: list[str], account_id: str | None, open_only: bool, text: str | None) -> str:
    parts = []
    if projects:
        parts.append("project in (" + ", ".join(_q(p) for p in projects) + ")")
    if account_id:
        parts.append(f"assignee = {_q(account_id)}")
    if open_only:
        parts.append("statusCategory != Done")
    t = (text or "").strip()
    if t:
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*-\d+", t):
            parts.append(f"(key = {_q(t.upper())} OR text ~ {_q(t)})")
        else:
            parts.append(f"text ~ {_q(t)}")
    return (" AND ".join(parts) or "created is not EMPTY") + " ORDER BY updated DESC"


def requirement(story: Story, extra: dict) -> str:
    """The chat message a Build starts with."""
    lines = [f"Jira {story.type.lower() or 'story'} {story.key}: {story.summary}"]
    if story.description:
        lines += ["", story.description]
    if extra.get("acceptance"):
        lines += ["", "Acceptance criteria:", extra["acceptance"]]
    if extra.get("subtasks"):
        lines += ["", "Sub-tasks:"] + [f"- {t['key']}: {t['summary']}" for t in extra["subtasks"]]
    if extra.get("components") or extra.get("labels"):
        lines += ["", "Jira components / labels: " + ", ".join([*extra.get("components", []), *extra.get("labels", [])])]
    text = "\n".join(lines).strip()
    return text[:19_000]


# ---------- account lookups (cached; one Jira call per member per 30 minutes) ----------

_accounts: dict[tuple[str, str], tuple[float, str | None]] = {}
_lock = threading.Lock()


def cached_account(site: str, email: str, look: callable) -> str | None:
    k = (site, email.lower())
    with _lock:
        hit = _accounts.get(k)
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    acc = look()
    with _lock:
        _accounts[k] = (time.time(), acc)
    return acc


def forget_accounts() -> None:
    with _lock:
        _accounts.clear()
