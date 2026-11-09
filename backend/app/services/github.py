"""GitHub (Chunk 9): Push to Git for approved plans.

Connected once per workspace with a fine-grained personal access token (Contents: read and write,
Pull requests: read and write, Metadata: read) limited to the repos nowBuilder may use. Each
ServiceNow instance maps to a repo and a base branch (`Integration.config["repos"][instance_id]`).

A push writes the plan's files to a branch `nowbuilder/<story or plan>` in one commit (Git data
API: tree on top of the branch, commit, move the ref) and opens a pull request into the base
branch, or reuses the open one. Only the plan's files change; everything else in the repo stays.
Paths follow the repo's `sfdx-project.json` default package directory (`force-app` if none).
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass

import httpx

API = "https://api.github.com"
TIMEOUT = 30.0
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^(?!/)(?!.*//)(?!.*\.\.)(?!.*@\{)[A-Za-z0-9._/-]{1,200}(?<![./])$")


class GitHubError(Exception):
    """Shown to the user as is."""


def slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:n].rstrip("-") or "plan"


def branch_name(title: str, jira_key: str | None) -> str:
    return f"nowbuilder/{jira_key + '-' if jira_key else ''}{slug(title)}"


def valid_branch(name: str) -> bool:
    return bool(BRANCH_RE.match(name or "")) and not name.endswith(".lock")


@dataclass
class PushResult:
    branch: str
    base: str
    commit: str | None
    changed: bool
    files: int
    pr_number: int
    pr_url: str
    pr_state: str
    pr_created: bool


class GitHubClient:
    def __init__(self, token: str, transport: httpx.BaseTransport | None = None):
        self.http = httpx.Client(base_url=API, timeout=TIMEOUT, transport=transport, headers={
            "Authorization": f"Bearer {token.strip()}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nowBuilder"})

    def close(self) -> None:
        self.http.close()

    def _call(self, method: str, path: str, ok404: bool = False, **kw):
        try:
            r = self.http.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise GitHubError("Couldn't reach GitHub. Try again in a moment.") from e
        if r.status_code == 404 and ok404:
            return None
        msg = ""
        if r.status_code >= 400 and r.content:
            try:
                body = r.json()
                msg = body.get("message", "") if isinstance(body, dict) else ""
            except ValueError:
                pass
        if r.status_code == 401:
            raise GitHubError("GitHub didn't accept the token. An admin can reconnect GitHub in Settings → GitHub.")
        if r.status_code == 403 and "rate limit" in msg.lower():
            raise GitHubError("GitHub is limiting requests right now. Try again in a few minutes.")
        if r.status_code == 403:
            raise GitHubError("The GitHub token doesn't have permission for this. Give it Contents and Pull requests (read and write) on this repo.")
        if r.status_code == 404:
            raise GitHubError("GitHub couldn't find that repo or branch, or the token can't see it.")
        if r.status_code == 409 and "empty" in msg.lower():
            raise GitHubError("The repository is empty. Add a first commit (a README is enough), then push again.")
        if r.status_code >= 400:
            raise GitHubError(f"GitHub said: {msg or f'error {r.status_code}'}.")
        return r.json() if r.content else {}

    # ----- account and repos -----
    def user(self) -> dict:
        u = self._call("GET", "/user")
        return {"login": u.get("login"), "name": u.get("name")}

    def repos(self) -> list[dict]:
        out = []
        for page in range(1, 6):
            batch = self._call("GET", "/user/repos", params={"per_page": 100, "page": page, "sort": "updated"})
            out += [{"full_name": r["full_name"], "default_branch": r.get("default_branch") or "main", "private": r.get("private", False),
                     "can_push": (r.get("permissions") or {}).get("push", True)} for r in batch]
            if len(batch) < 100:
                break
        return out

    def branches(self, repo: str) -> list[str]:
        _check_repo(repo)
        out = []
        for page in range(1, 4):
            batch = self._call("GET", f"/repos/{repo}/branches", params={"per_page": 100, "page": page})
            out += [b["name"] for b in batch]
            if len(batch) < 100:
                break
        return out

    def _head(self, repo: str, branch: str) -> str | None:
        ref = self._call("GET", f"/repos/{repo}/git/ref/heads/{branch}", ok404=True)
        return ref["object"]["sha"] if ref else None

    def package_dir(self, repo: str, ref: str) -> str:
        f = self._call("GET", f"/repos/{repo}/contents/sfdx-project.json", ok404=True, params={"ref": ref})
        if not f or "content" not in f:
            return "force-app"
        try:
            dirs = json.loads(base64.b64decode(f["content"]).decode("utf-8")).get("packageDirectories") or []
        except (ValueError, UnicodeDecodeError):
            return "force-app"
        main = next((d for d in dirs if d.get("default")), dirs[0] if dirs else None)
        path = (main or {}).get("path") or "force-app"
        return path.strip("/").removeprefix("./") or "force-app"

    def pull_state(self, repo: str, number: int) -> str:
        pr = self._call("GET", f"/repos/{repo}/pulls/{number}")
        return "merged" if pr.get("merged") else pr.get("state", "open")

    # ----- push -----
    def push(self, repo: str, base: str, branch: str, files: dict[str, str], message: str, title: str, body: str) -> PushResult:
        """Commit `files` (SFDX paths under force-app/) to `branch` and open or reuse a PR into `base`."""
        _check_repo(repo)
        if not valid_branch(branch):
            raise GitHubError("That branch name isn't valid. Use letters, numbers, - _ . and /.")
        if branch == base:
            raise GitHubError("Push to a new branch, not the base branch, so the change goes through a pull request.")
        base_sha = self._head(repo, base)
        if base_sha is None:
            raise GitHubError(f"The branch {base} doesn't exist in {repo}. An admin can change it in Settings → GitHub.")
        head_sha = self._head(repo, branch)
        parent = head_sha or base_sha
        root = self.package_dir(repo, parent)
        parent_commit = self._call("GET", f"/repos/{repo}/git/commits/{parent}")
        tree_items = [{"path": _repo_path(p, root), "mode": "100644", "type": "blob", "content": c} for p, c in sorted(files.items())]
        tree = self._call("POST", f"/repos/{repo}/git/trees", json={"base_tree": parent_commit["tree"]["sha"], "tree": tree_items})
        changed = tree["sha"] != parent_commit["tree"]["sha"]
        commit_sha = None
        if changed:
            commit = self._call("POST", f"/repos/{repo}/git/commits", json={"message": message, "tree": tree["sha"], "parents": [parent]})
            commit_sha = commit["sha"]
            if head_sha:
                self._call("PATCH", f"/repos/{repo}/git/refs/heads/{branch}", json={"sha": commit_sha, "force": False})
            else:
                self._call("POST", f"/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": commit_sha})
        elif not head_sha:
            raise GitHubError(f"These files are already the same on {base}, so there's nothing to push.")
        owner = repo.split("/")[0]
        existing = self._call("GET", f"/repos/{repo}/pulls", params={"head": f"{owner}:{branch}", "state": "open", "per_page": 1})
        if existing:
            pr, created = existing[0], False
        else:
            pr = self._call("POST", f"/repos/{repo}/pulls", json={"title": title, "head": branch, "base": base, "body": body})
            created = True
        return PushResult(branch=branch, base=base, commit=commit_sha or head_sha, changed=changed, files=len(files),
                          pr_number=pr["number"], pr_url=pr["html_url"], pr_state="open", pr_created=created)


def _check_repo(repo: str) -> None:
    if not REPO_RE.match(repo or ""):
        raise GitHubError("Choose a repository as owner/name.")


def _repo_path(path: str, root: str) -> str:
    path = path.lstrip("/")
    if path.startswith("force-app/") and root != "force-app":
        return root + path[len("force-app"):]
    return path
