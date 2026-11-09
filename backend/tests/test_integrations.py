"""Jira stories (Push to Git comes back with deploys in Chunk 4). The real Jira and GitHub clients run against
in-memory fakes of the two REST APIs (httpx.MockTransport), so request shapes are checked too."""
import base64
import json
import re

import httpx
import pytest

from app.db import SessionLocal
from app.models import Chat, Integration
from app.services import integrations as integ_svc
from app.services.github import GitHubClient, branch_name
from app.services.jira import JiraClient, adf_text, build_jql

from .conftest import connect_instance
from .test_instances import ScriptedLLM, _ready_ai
from .test_workspace import join


@pytest.fixture
def env(client, auth, snow, monkeypatch):
    """A workspace with a connected instance and a ready AI provider."""
    connect_instance(client, auth)
    llm = ScriptedLLM([[{"type": "text", "text": "Here is how I would build it."}]])
    _ready_ai(client, auth, monkeypatch, llm)
    return {"h": auth, "llm": llm}

SITE = "https://acme.atlassian.net"


def adf(*paras):
    return {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": p}]} for p in paras]}


class FakeJira:
    def __init__(self):
        self.comments: list[tuple[str, dict]] = []
        self.searches: list[str] = []
        self.users = [{"accountId": "acc-vasu", "emailAddress": "vasu@example.com", "accountType": "atlassian", "displayName": "Vasu"}]
        self.token = "jira-token-1234"
        self.issues = {
            "SCRUM-21": {"summary": "New POM LWC", "status": ("In Progress", "indeterminate"), "type": "Task", "assignee": "acc-vasu",
                         "description": {"type": "doc", "version": 1, "content": [
                             {"type": "paragraph", "content": [{"type": "text", "text": "Build an LWC modal called newAgendaItem."}]},
                             {"type": "bulletList", "content": [
                                 {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Screen 1 asks for a category"}]}]},
                                 {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Screen 2 shows extra fields"}]}]}]}]},
                         "acceptance": adf("Record is created", "Toast shows the record link"),
                         "attachments": [{"id": "1", "filename": "brd.txt", "size": 30, "content": f"{SITE}/rest/api/3/attachment/content/1", "mimeType": "text/plain"},
                                         {"id": "2", "filename": "mock.png", "size": 3000, "content": f"{SITE}/rest/api/3/attachment/content/2", "mimeType": "image/png"}]},
            "SCRUM-20": {"summary": "New LWC Component", "status": ("Done", "done"), "type": "Task", "assignee": "acc-vasu", "description": adf("Old one")},
            "AT-1": {"summary": "Epic for agendas", "status": ("To Do", "new"), "type": "Epic", "assignee": None, "description": None},
        }

    def _issue(self, key):
        i = self.issues[key]
        return {"key": key, "fields": {
            "summary": i["summary"], "status": {"name": i["status"][0], "statusCategory": {"key": i["status"][1]}},
            "priority": {"name": "Medium"}, "issuetype": {"name": i["type"]}, "description": i["description"], "updated": "2026-10-17T10:00:00.000+0530",
            "assignee": {"displayName": "Vasu"} if i["assignee"] else None, "project": {"key": key.split("-")[0]},
            "customfield_10050": i.get("acceptance"), "attachment": i.get("attachments", []), "labels": ["council"], "subtasks": [], "components": []}}

    def handler(self, req: httpx.Request) -> httpx.Response:
        auth = req.headers.get("authorization", "")
        if base64.b64decode(auth.split(" ", 1)[1]).decode() != f"vasu@acme.com:{self.token}":
            return httpx.Response(401, json={"errorMessages": ["Unauthorized"]})
        p = req.url.path
        if p == "/rest/api/3/myself":
            return httpx.Response(200, json={"accountId": "acc-vasu", "displayName": "Vasu D", "emailAddress": "vasu@acme.com"})
        if p == "/rest/api/3/project/search":
            return httpx.Response(200, json={"values": [{"key": "SCRUM", "name": "Scrum"}, {"key": "AT", "name": "Agenda"}], "isLast": True})
        if p == "/rest/api/3/user/search":
            q = req.url.params["query"].lower()
            return httpx.Response(200, json=[u for u in self.users if u["emailAddress"] == q])
        if p == "/rest/api/3/search/jql":
            body = json.loads(req.content)
            jql = body["jql"]
            self.searches.append(jql)
            keys = [k for k, i in self.issues.items()
                    if ("assignee" not in jql or f'"{i["assignee"]}"' in jql)
                    and ("statusCategory != Done" not in jql or i["status"][1] != "done")
                    and ("project in" not in jql or f'"{k.split("-")[0]}"' in jql)
                    and (not (m := re.search(r'text ~ "([^"]*)"', jql)) or m[1].lower() in f"{k} {i['summary']}".lower())]
            return httpx.Response(200, json={"issues": [self._issue(k) for k in keys], "isLast": True})
        if p.startswith("/rest/api/3/issue/") and p.endswith("/comment"):
            self.comments.append((p.split("/")[5], json.loads(req.content)["body"]))
            return httpx.Response(201, json={"id": "c1"})
        if p.startswith("/rest/api/3/issue/"):
            key = p.rsplit("/", 1)[1]
            if key not in self.issues:
                return httpx.Response(404, json={"errorMessages": ["Issue does not exist"]})
            return httpx.Response(200, json={**self._issue(key), "names": {"customfield_10050": "Acceptance Criteria", "summary": "Summary"}})
        if p == "/rest/api/3/attachment/content/1":
            return httpx.Response(200, content=b"Agenda categories: Bid Award")
        return httpx.Response(404, json={"errorMessages": ["no route"]})


class FakeGitHub:
    def __init__(self):
        self.token = "github_pat_abcd"
        self.branches = {"acme/salesforce": {"main": "c0", "develop": "c0"}}
        self.commits = {"c0": {"tree": "t0", "parents": []}}
        self.trees = {"t0": {"force-app/main/default/classes/Old.cls": "old", "README.md": "hi"}}
        self.pulls: list[dict] = []
        self.sfdx = None  # sfdx-project.json content, or None
        self.n = 0

    def _new(self, prefix):
        self.n += 1
        return f"{prefix}{self.n}"

    def handler(self, req: httpx.Request) -> httpx.Response:
        if req.headers.get("authorization") != f"Bearer {self.token}":
            return httpx.Response(401, json={"message": "Bad credentials"})
        p, m = req.url.path, req.method
        body = json.loads(req.content) if req.content else {}
        if p == "/user":
            return httpx.Response(200, json={"login": "vasu-dev", "name": "Vasu"})
        if p == "/user/repos":
            return httpx.Response(200, json=[{"full_name": "acme/salesforce", "default_branch": "main", "private": True, "permissions": {"push": True}}])
        parts = p.strip("/").split("/")
        repo = "/".join(parts[1:3])
        if repo not in self.branches:
            return httpx.Response(404, json={"message": "Not Found"})
        rest = "/".join(parts[3:])
        heads = self.branches[repo]
        if rest == "branches":
            return httpx.Response(200, json=[{"name": b} for b in heads])
        if rest.startswith("git/ref/heads/"):
            b = rest[len("git/ref/heads/"):]
            return httpx.Response(200, json={"object": {"sha": heads[b]}}) if b in heads else httpx.Response(404, json={"message": "Not Found"})
        if rest == "contents/sfdx-project.json":
            if self.sfdx is None:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, json={"content": base64.b64encode(json.dumps(self.sfdx).encode()).decode()})
        if rest.startswith("git/commits/") and m == "GET":
            sha = rest.rsplit("/", 1)[1]
            return httpx.Response(200, json={"sha": sha, "tree": {"sha": self.commits[sha]["tree"]}})
        if rest == "git/trees":
            files = dict(self.trees[body["base_tree"]])
            for item in body["tree"]:
                files[item["path"]] = item["content"]
            sha = next((s for s, f in self.trees.items() if f == files), None) or self._new("t")
            self.trees[sha] = files
            return httpx.Response(201, json={"sha": sha})
        if rest == "git/commits":
            sha = self._new("c")
            self.commits[sha] = {"tree": body["tree"], "parents": body["parents"], "message": body["message"]}
            return httpx.Response(201, json={"sha": sha})
        if rest == "git/refs":
            heads[body["ref"].removeprefix("refs/heads/")] = body["sha"]
            return httpx.Response(201, json={})
        if rest.startswith("git/refs/heads/") and m == "PATCH":
            heads[rest[len("git/refs/heads/"):]] = body["sha"]
            return httpx.Response(200, json={})
        if rest == "pulls" and m == "GET":
            head = req.url.params["head"].split(":", 1)[1]
            return httpx.Response(200, json=[pr for pr in self.pulls if pr["head"] == head and pr["state"] == "open"][:1])
        if rest == "pulls" and m == "POST":
            pr = {"number": len(self.pulls) + 1, "html_url": f"https://github.com/{repo}/pull/{len(self.pulls) + 1}", "state": "open",
                  "merged": False, **body}
            self.pulls.append(pr)
            return httpx.Response(201, json=pr)
        if rest.startswith("pulls/"):
            pr = self.pulls[int(rest.split("/")[1]) - 1]
            return httpx.Response(200, json=pr)
        return httpx.Response(404, json={"message": "Not Found"})

    def files_on(self, repo, branch):
        return self.trees[self.commits[self.branches[repo][branch]]["tree"]]


@pytest.fixture
def fakes(monkeypatch):
    jira, gh = FakeJira(), FakeGitHub()
    from app.security import decrypt
    monkeypatch.setattr(integ_svc, "make_jira", lambda i: JiraClient(i.config["site"], i.config["email"], decrypt(i.token_enc), transport=httpx.MockTransport(jira.handler)))
    monkeypatch.setattr(integ_svc, "make_github", lambda i: GitHubClient(decrypt(i.token_enc), transport=httpx.MockTransport(gh.handler)))
    monkeypatch.setattr(integ_svc, "COMMENTS_WAIT", True)
    from app.services import jira as jira_mod
    jira_mod.forget_accounts()
    return {"jira": jira, "gh": gh}


def connect_jira(client, h, **kw):
    body = {"site": "acme.atlassian.net", "email": "vasu@acme.com", "token": "jira-token-1234", "projects": ["SCRUM", "AT"], **kw}
    return client.put("/api/integrations/jira", json=body, headers=h)


# ---------- unit ----------

def test_adf_to_text_keeps_lists_and_paragraphs():
    doc = FakeJira().issues["SCRUM-21"]["description"]
    assert adf_text(doc) == "Build an LWC modal called newAgendaItem.\n\n- Screen 1 asks for a category\n- Screen 2 shows extra fields"
    assert adf_text(None) == "" and adf_text("plain") == "plain"


def test_jql_quotes_values_and_finds_keys():
    jql = build_jql(["SCRUM"], "acc-1", True, 'scrum-21')
    assert jql == 'project in ("SCRUM") AND assignee = "acc-1" AND statusCategory != Done AND (key = "SCRUM-21" OR text ~ "scrum-21") ORDER BY updated DESC'
    assert 'text ~ "a \\"b\\""' in build_jql([], None, False, 'a "b"')
    assert branch_name("Invoice approval!", "SCRUM-21") == "nowbuilder/SCRUM-21-invoice-approval"


# ---------- Settings → Jira / GitHub ----------

def test_connect_jira_checks_the_token_and_never_returns_it(client, auth, fakes):
    fakes["jira"].token = "other"
    r = connect_jira(client, auth)
    assert r.status_code == 400 and "didn't accept that email and API token" in r.json()["detail"]
    fakes["jira"].token = "jira-token-1234"
    assert connect_jira(client, auth, projects=["NOPE"]).json()["detail"] == "nowBuilder's Jira account can't see space NOPE. Check the key (like SCRUM in SCRUM-21)."
    r = connect_jira(client, auth)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["site"] == SITE and j["account"] == "Vasu D" and j["token_masked"] == "••••••••1234" and "jira-token" not in json.dumps(j)
    # saving again without the token keeps the saved one
    assert connect_jira(client, auth, token=None, projects=["SCRUM"]).json()["projects"] == ["SCRUM"]
    with SessionLocal() as db:
        assert "jira-token" not in db.query(Integration).one().token_enc
    assert client.get("/api/integrations", headers=auth).json()["jira"]["connected"] is True


def test_only_admins_manage_integrations(client, auth, fakes, env):
    dev = join(client, auth, "dev@example.com", "developer")
    assert connect_jira(client, dev).status_code == 403
    assert client.get("/api/integrations", headers=dev).json()["can_manage"] is False
    r = client.get("/api/jira/stories", headers=dev)
    assert r.status_code == 409 and "Ask a workspace admin" in r.json()["detail"]


# ---------- stories ----------

def test_stories_assigned_to_me_open_and_all(client, auth, fakes):
    connect_jira(client, auth)
    r = client.get("/api/jira/stories", headers=auth).json()
    assert r["scope"] == "mine" and [s["key"] for s in r["stories"]] == ["SCRUM-21"]
    assert 'assignee = "acc-vasu"' in fakes["jira"].searches[-1] and 'project in ("SCRUM", "AT")' in fakes["jira"].searches[-1]
    s = r["stories"][0]
    assert s["status"] == "In Progress" and s["status_category"] == "indeterminate" and s["type"] == "Task" and s["url"] == f"{SITE}/browse/SCRUM-21"
    every = client.get("/api/jira/stories?scope=all&open=false", headers=auth).json()
    assert [s["key"] for s in every["stories"]] == ["SCRUM-21", "SCRUM-20", "AT-1"]


def test_member_without_a_jira_user_sees_the_projects_stories(client, auth, fakes, env):
    connect_jira(client, auth)
    dev = join(client, auth, "dev@example.com", "developer")
    r = client.get("/api/jira/stories", headers=dev).json()
    assert r["scope"] == "all" and "dev@example.com" in r["note"] and len(r["stories"]) == 2


def test_story_details_include_acceptance_criteria_and_attachments(client, auth, fakes):
    connect_jira(client, auth)
    d = client.get("/api/jira/stories/scrum-21", headers=auth).json()
    assert d["acceptance"] == "Record is created\n\nToast shows the record link"
    assert d["attachments"] == [{"name": "brd.txt", "size": 30, "readable": True}, {"name": "mock.png", "size": 3000, "readable": False}]
    assert client.get("/api/jira/stories/not a key", headers=auth).status_code == 400
    assert client.get("/api/jira/stories/SCRUM-99", headers=auth).status_code == 502


def test_build_from_story_starts_a_linked_chat_with_its_attachments(client, env, fakes):
    h = env["h"]
    connect_jira(client, h)
    r = client.post("/api/jira/stories/SCRUM-21/build", json={}, headers=h).json()
    assert r["existing"] is False and r["attachments"] == ["brd.txt"] and r["skipped_attachments"] == ["mock.png"]
    req = r["requirement"]
    assert req.startswith("Jira task SCRUM-21: New POM LWC\n\nBuild an LWC modal") and "Acceptance criteria:\nRecord is created" in req
    chat = r["chat"]
    assert chat["title"] == "SCRUM-21: New POM LWC" and chat["jira"]["url"] == f"{SITE}/browse/SCRUM-21" and "pending_attachments" not in chat["jira"]
    # the stories list now points at the chat, and Build opens it instead of making another
    assert client.get("/api/jira/stories", headers=h).json()["stories"][0]["chat_id"] == chat["id"]
    again = client.post("/api/jira/stories/SCRUM-21/build", json={}, headers=h).json()
    assert again["existing"] is True and again["chat"]["id"] == chat["id"]
    # first message: the story's attachment goes with it
    r = client.post(f"/api/chats/{chat['id']}/messages", data={"text": req, "story": "true"}, headers=h)
    assert r.status_code == 200
    assert "Agenda categories: Bid Award" in env["llm"].seen[0]["messages"][0]["content"]
    with SessionLocal() as db:
        c = db.get(Chat, chat["id"])
        user_msg = next(m for m in c.messages if m.role == "user")
        assert user_msg.attachments[0]["name"] == "brd.txt" and "Agenda categories: Bid Award" in user_msg.attachment_text
        assert "pending_attachments" not in c.jira


def test_viewer_cannot_build_from_a_story(client, auth, fakes, env):
    connect_jira(client, auth)
    viewer = join(client, auth, "view@example.com", "viewer")
    assert client.post("/api/jira/stories/SCRUM-21/build", json={}, headers=viewer).status_code == 403
