"""Platform admin (owner's design, 19 Oct): approval sign-up, a plan and limits per workspace,
turning a workspace off and on. Only emails in NOWBUILDER_PLATFORM_ADMINS can do this."""
import pytest

from app.config import get_settings
from app.services import ai_provider

from .test_workspace import connect, invite, join, register

ADMIN = "vasu@example.com"


@pytest.fixture
def platform(client, snow, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "platform_admins", f"{ADMIN.upper()}, other@nowbuilder.dev")
    monkeypatch.setattr(s, "signup_mode", "approval")
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    admin = register(client, ADMIN, "Vasu")
    return {"admin": admin}


def rows(client, h):
    r = client.get("/api/platform/workspaces", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def ws_of(data, email):
    return next(w for w in data["workspaces"] if w["owner"]["email"] == email)


def test_new_sign_up_waits_for_approval_and_the_admin_never_does(client, platform):
    me = client.get("/api/auth/me", headers=platform["admin"]).json()
    assert me["is_platform_admin"] is True
    assert client.get("/api/workspace", headers=platform["admin"]).status_code == 200  # admin's own workspace works at once
    acme = register(client, "owner@acme.com", "Ana")
    r = client.get("/api/workspace", headers=acme)
    assert r.status_code == 403 and r.json()["code"] == "pending" and "waiting for approval" in r.json()["detail"]
    assert client.get("/api/instances", headers=acme).status_code == 403
    assert client.get("/api/auth/me", headers=acme).json()["is_platform_admin"] is False
    # only platform admins see the Platform page
    assert client.get("/api/platform/workspaces", headers=acme).status_code == 403
    data = rows(client, platform["admin"])
    assert data["signup"] == "approval" and data["counts"]["pending"] == 1
    assert data["workspaces"][0]["owner"]["email"] == "owner@acme.com"  # waiting ones first
    w = ws_of(data, "owner@acme.com")
    assert w["status"] == "pending" and w["plan"] == "standard" and w["instances"] == {"max": 2, "used": 0, "custom": False}
    # approve on the Starter plan: 1 instance, 2 members
    r = client.patch(f"/api/platform/workspaces/{w['id']}", json={"status": "active", "plan": "starter"}, headers=platform["admin"])
    assert r.status_code == 200, r.text
    w = r.json()["workspace"]
    assert w["status"] == "active" and w["approved_by"] == ADMIN and w["instances"]["max"] == 1 and w["members"]["max"] == 2
    limits = client.get("/api/workspace", headers=acme).json()["limits"]
    assert limits["instances"]["max"] == 1 and limits["members"]["max"] == 2 and limits["plan"] == "Starter"


def _approve(client, admin, email, **body):
    w = ws_of(rows(client, admin), email)
    r = client.patch(f"/api/platform/workspaces/{w['id']}", json={"status": "active", **body}, headers=admin)
    assert r.status_code == 200, r.text
    return w["id"]


def test_limits_follow_the_plan_and_overrides(client, platform):
    acme = register(client, "owner@acme.com", "Ana")
    wid = _approve(client, platform["admin"], "owner@acme.com", plan="starter")
    assert connect(client, acme, "Dev", "dev-one").status_code == 201
    second = connect(client, acme, "UAT", "uat-one")
    assert second.status_code == 409 and "at most 1 ServiceNow instance" in second.json()["detail"]
    assert invite(client, acme, "a@acme.com", "developer").status_code == 201
    third = invite(client, acme, "b@acme.com", "viewer")
    assert third.status_code == 409 and "at most 2 members" in third.json()["detail"]
    # the customer upgrades: 3 instances and 4 members (custom numbers on top of the plan)
    r = client.patch(f"/api/platform/workspaces/{wid}", json={"max_instances": 3, "max_members": 4}, headers=platform["admin"])
    w = r.json()["workspace"]
    assert w["instances"] == {"max": 3, "used": 1, "custom": True} and w["members"]["max"] == 4 and w["members"]["invites"] == 1
    assert connect(client, acme, "UAT", "uat-one").status_code == 201
    assert invite(client, acme, "b@acme.com", "viewer").status_code == 201
    # back to the plan's numbers; going below what's used removes nothing, it only stops adding
    r = client.patch(f"/api/platform/workspaces/{wid}", json={"max_instances": None, "max_members": None}, headers=platform["admin"])
    w = r.json()["workspace"]
    assert w["instances"] == {"max": 1, "used": 2, "custom": False}
    assert len(client.get("/api/instances", headers=acme).json()) == 2
    assert connect(client, acme, "Prod", "prod-one", "Production").status_code == 409
    bad = client.patch(f"/api/platform/workspaces/{wid}", json={"plan": "gold"}, headers=platform["admin"])
    assert bad.status_code == 400 and "plans" in bad.json()["detail"]
    assert client.patch(f"/api/platform/workspaces/{wid}", json={"max_instances": 0}, headers=platform["admin"]).status_code == 422


def test_turning_a_workspace_off_and_on_keeps_its_data(client, platform):
    acme = register(client, "owner@acme.com", "Ana")
    wid = _approve(client, platform["admin"], "owner@acme.com")
    connect(client, acme, "Dev", "dev-one")
    dev = join(client, acme, "dev@acme.com", "developer")  # invited people join the approved workspace, no approval of their own
    assert client.get("/api/workspace", headers=dev).status_code == 200
    assert len(rows(client, platform["admin"])["workspaces"]) == 2  # the invitee's empty own workspace isn't listed
    client.patch(f"/api/platform/workspaces/{wid}", json={"status": "suspended", "note": "Trial ended"}, headers=platform["admin"])
    for h in (acme, dev):
        r = client.get("/api/instances", headers=h)
        assert r.status_code == 403 and r.json()["code"] == "suspended"
    w = ws_of(rows(client, platform["admin"]), "owner@acme.com")
    assert w["status"] == "suspended" and w["note"] == "Trial ended"
    assert client.patch(f"/api/platform/workspaces/{wid}", json={"status": "pending"}, headers=platform["admin"]).status_code == 400
    mine = ws_of(rows(client, platform["admin"]), ADMIN)
    assert mine["platform_admin"] is True
    assert client.patch(f"/api/platform/workspaces/{mine['id']}", json={"status": "suspended"}, headers=platform["admin"]).status_code == 400
    client.patch(f"/api/platform/workspaces/{wid}", json={"status": "active"}, headers=platform["admin"])
    assert [o["name"] for o in client.get("/api/instances", headers=acme).json()] == ["Dev"]


def test_open_sign_up_and_existing_workspaces_keep_working(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_mode", "open")
    h = register(client, "solo@example.com", "Solo")
    assert client.get("/api/workspace", headers=h).status_code == 200
    assert client.get("/api/platform/workspaces", headers=h).status_code == 403  # not a platform admin
    monkeypatch.setattr(get_settings(), "signup_mode", "")
    monkeypatch.setattr(get_settings(), "environment", "production")
    assert get_settings().signup_needs_approval is True  # hosted default


# ---------- 22 Oct: one workspace per person, admins in the app, deleting a workspace ----------

def test_opening_the_app_creates_one_workspace_even_with_parallel_requests(client):
    import threading

    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Membership, User
    from app.services.workspace import ensure_membership
    with SessionLocal() as db:
        u = User(email="race@example.com", first_name="R", last_name="X", password_hash="x")
        db.add(u)
        db.commit()
        uid = u.id
    barrier = threading.Barrier(3)

    def first_request():
        with SessionLocal() as db:
            user = db.get(User, uid)
            barrier.wait()
            ensure_membership(db, user)
    threads = [threading.Thread(target=first_request) for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Membership).where(Membership.user_id == uid)) == 1


def test_empty_duplicate_workspaces_are_closed_and_ones_with_data_are_marked_not_in_use(client, platform):
    from app.db import SessionLocal, _one_active_membership, engine
    from app.models import Chat, Membership, User, Workspace
    from sqlalchemy import select, text
    with engine.begin() as conn:  # an older database without the index
        conn.execute(text("DROP INDEX IF EXISTS uq_one_active_membership"))
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == ADMIN))
        for name, with_chat in (("Empty copy", False), ("Copy with a chat", True)):
            w = Workspace(name=name, owner_id=u.id, status="active")
            db.add(w)
            db.flush()
            db.add(Membership(workspace_id=w.id, user_id=u.id, role="owner", status="active",
                              created_at=__import__("datetime").datetime(2026, 10, 1, tzinfo=__import__("datetime").UTC)))
            if with_chat:
                db.add(Chat(user_id=u.id, workspace_id=w.id, title="old"))
        db.commit()
    _one_active_membership()
    data = rows(client, platform["admin"])
    names = {w["name"]: w for w in data["workspaces"]}
    assert "Empty copy" not in names and names["Copy with a chat"]["in_use"] is False and names["Vasu's workspace"]["in_use"] is True
    # deleting the copy with data leaves one workspace; then the database can hold the rule
    h = platform["admin"]
    wid = names["Copy with a chat"]["id"]
    wrong = client.request("DELETE", f"/api/platform/workspaces/{wid}", json={"confirm": "copy"}, headers=h)
    assert wrong.status_code == 400 and "Type the workspace name" in wrong.json()["detail"]
    ok = client.request("DELETE", f"/api/platform/workspaces/{wid}", json={"confirm": "Copy with a chat"}, headers=h)
    assert ok.status_code == 200 and ok.json()["deleted"] == "Copy with a chat"
    _one_active_membership()
    from sqlalchemy import inspect
    assert "uq_one_active_membership" in {i["name"] for i in inspect(engine).get_indexes("memberships")}


def test_platform_admins_are_added_and_removed_in_the_app(client, platform):
    h = platform["admin"]
    data = client.get("/api/platform/admins", headers=h).json()["admins"]
    assert [(a["email"], a["source"]) for a in data] == [("other@nowbuilder.dev", "server"), (ADMIN, "server")]
    ops = register(client, "ops@acme.com", "Ops")
    assert client.get("/api/platform/workspaces", headers=ops).status_code == 403
    r = client.post("/api/platform/admins", json={"email": "Ops@Acme.com"}, headers=h)
    assert r.status_code == 201 and r.json()["admins"][-1] == {"email": "ops@acme.com", "name": "Ops K", "signed_up": True, "is_me": False,
                                                                "source": "app", "added_by": ADMIN, "added_at": r.json()["admins"][-1]["added_at"]}
    assert client.get("/api/auth/me", headers=ops).json()["is_platform_admin"] is True
    assert client.get("/api/workspace", headers=ops).status_code == 200  # a platform admin's own workspace works at once
    assert client.post("/api/platform/admins", json={"email": "ops@acme.com"}, headers=h).status_code == 409
    # someone not signed up yet can be added too
    assert client.post("/api/platform/admins", json={"email": "later@acme.com"}, headers=h).json()["admins"][-1]["signed_up"] is False
    # server admins and yourself can't be removed in the app
    assert "set on the server" in client.delete("/api/platform/admins/other@nowbuilder.dev", headers=h).json()["detail"]
    assert "yourself" in client.delete("/api/platform/admins/ops@acme.com", headers=ops).json()["detail"]
    assert client.delete("/api/platform/admins/ops@acme.com", headers=h).status_code == 200
    assert client.get("/api/platform/workspaces", headers=ops).status_code == 403
    assert client.get("/api/platform/summary", headers=h).json() == {"pending": 0}


def test_deleting_a_workspace_removes_its_data_and_its_people_start_fresh(client, platform):
    from app.db import SessionLocal
    from app.models import Chat, Instance
    from sqlalchemy import func, select
    acme = register(client, "owner@acme.com", "Ana")
    wid = _approve(client, platform["admin"], "owner@acme.com")
    connect(client, acme, "Dev", "dev-one")
    dev = join(client, acme, "dev@acme.com", "developer")
    with SessionLocal() as db:
        from app.models import User
        owner = db.scalar(select(User.id).where(User.email == "owner@acme.com"))
        db.add(Chat(user_id=owner, workspace_id=wid, title="a chat"))
        db.commit()
    # you can't delete the workspace you're using
    mine = ws_of(rows(client, platform["admin"]), ADMIN)
    r = client.request("DELETE", f"/api/platform/workspaces/{mine['id']}", json={"confirm": mine["name"]}, headers=platform["admin"])
    assert r.status_code == 400 and "you're using" in r.json()["detail"]
    assert client.request("DELETE", f"/api/platform/workspaces/{wid}", json={"confirm": "Ana's workspace"}, headers=acme).status_code == 403
    r = client.request("DELETE", f"/api/platform/workspaces/{wid}", json={"confirm": "Ana's workspace"}, headers=platform["admin"])
    assert r.status_code == 200 and all(w["id"] != wid for w in r.json()["workspaces"])
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Instance).where(Instance.workspace_id == wid)) == 0
        assert db.scalar(select(func.count()).select_from(Chat).where(Chat.workspace_id == wid)) == 0
    # accounts stay; next time they get a new workspace of their own, waiting for approval
    for h in (acme, dev):
        r = client.get("/api/workspace", headers=h)
        assert r.status_code == 403 and r.json()["code"] == "pending"
