"""Workspace, members, roles, invites, per-instance access and the owner's limits
(3 active members including pending invites, 2 connected instances)."""
from datetime import UTC, datetime, timedelta

import pytest

from app.db import SessionLocal
from app.models import Invite
from app.services import ai_provider

from .conftest import connect_instance


def register(client, email, first="Asha"):
    r = client.post("/api/auth/register", json={"first_name": first, "last_name": "K", "email": email, "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def connect(client, h, name, host, instance_type="Development"):
    return connect_instance(client, h, name=name, url=host, instance_type=instance_type)


def invite(client, h, email, role, instance_ids=None):
    r = client.post("/api/workspace/invites", json={"email": email, "role": role, "instance_ids": instance_ids}, headers=h)
    return r


def join(client, owner_h, email, role, instance_ids=None, first="Asha"):
    r = invite(client, owner_h, email, role, instance_ids)
    assert r.status_code == 201, r.text
    token = r.json()["link"].rsplit("/", 1)[1]
    h = register(client, email, first)
    a = client.post(f"/api/invites/{token}/accept", headers=h)
    assert a.status_code == 200, a.text
    return h


@pytest.fixture
def team(client, auth, snow, monkeypatch):
    monkeypatch.setattr(ai_provider, "verify", lambda *a: ai_provider.VerifyResult(True, "ok"))
    dev = connect(client, auth, "Dev", "dev-one").json()
    return {"owner": auth, "dev_org": dev}


def test_existing_data_moves_into_the_owners_workspace(client, team):
    w = client.get("/api/workspace", headers=team["owner"]).json()
    assert w["me"]["role"] == "owner" and "manage_members" in w["me"]["permissions"] and w["workspace"]["name"] == "Vasu's workspace"
    assert w["limits"] == {"members": {"max": 3, "active": 1, "pending": 0}, "instances": {"max": 2, "used": 1}, "plan": "Standard"}
    orgs = client.get("/api/instances", headers=team["owner"]).json()
    assert [o["name"] for o in orgs] == ["Dev"] and orgs[0]["is_selected"] is True


def test_invite_link_join_and_shared_space(client, team):
    owner = team["owner"]
    chat = client.post("/api/chats", headers=owner).json()
    dev = join(client, owner, "asha@example.com", "developer")
    me = client.get("/api/workspace", headers=dev).json()
    assert me["me"]["role"] == "developer" and me["workspace"]["name"] == "Vasu's workspace"
    assert [o["name"] for o in client.get("/api/instances", headers=dev).json()] == ["Dev"]
    chats = client.get("/api/chats", headers=dev).json()
    assert [c["id"] for c in chats] == [chat["id"]] and chats[0]["by"] == "Vasu Dharavath"  # shared team space
    members = client.get("/api/workspace/members", headers=owner).json()
    assert {m["email"]: m["role"] for m in members["members"]} == {"vasu@example.com": "owner", "asha@example.com": "developer"}
    # the link works once
    with SessionLocal() as db:
        assert db.query(Invite).one().status == "accepted"


def test_invite_must_match_email_and_expire(client, team):
    r = invite(client, team["owner"], "asha@example.com", "viewer")
    token = r.json()["link"].rsplit("/", 1)[1]
    view = client.get(f"/api/invites/{token}").json()
    assert view["workspace"] == "Vasu's workspace" and view["role_label"] == "Viewer" and view["problem"] is None and view["has_account"] is False
    other = register(client, "someone@example.com")
    bad = client.post(f"/api/invites/{token}/accept", headers=other)
    assert bad.status_code == 403 and "asha@example.com" in bad.json()["detail"]
    with SessionLocal() as db:
        db.query(Invite).one().expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    asha = register(client, "asha@example.com")
    r = client.post(f"/api/invites/{token}/accept", headers=asha)
    assert r.status_code == 409 and "expired" in r.json()["detail"]
    assert client.get(f"/api/invites/{token}").json()["problem"].startswith("This invite has expired")


def test_member_limit_counts_pending_invites(client, team):
    owner = team["owner"]
    assert invite(client, owner, "a@example.com", "developer").status_code == 201
    second = invite(client, owner, "b@example.com", "viewer")
    assert second.status_code == 201
    third = invite(client, owner, "c@example.com", "viewer")
    assert third.status_code == 409 and "at most 3 members" in third.json()["detail"]
    client.delete(f"/api/workspace/invites/{second.json()['invite']['id']}", headers=owner)
    assert invite(client, owner, "c@example.com", "viewer").status_code == 201
    w = client.get("/api/workspace", headers=owner).json()
    assert w["limits"]["members"] == {"max": 3, "active": 1, "pending": 2}


def test_disabled_member_frees_a_seat_and_loses_access(client, team):
    owner = team["owner"]
    a = join(client, owner, "a@example.com", "developer")
    join(client, owner, "b@example.com", "viewer", first="Bo")
    assert invite(client, owner, "c@example.com", "viewer").status_code == 409  # 3 active
    members = client.get("/api/workspace/members", headers=owner).json()["members"]
    aid = next(m["id"] for m in members if m["email"] == "a@example.com")
    assert client.patch(f"/api/workspace/members/{aid}", json={"status": "disabled"}, headers=owner).status_code == 200
    r = client.get("/api/instances", headers=a)
    assert r.status_code == 403 and "turned off" in r.json()["detail"]
    c = invite(client, owner, "c@example.com", "viewer")
    assert c.status_code == 201
    back = client.patch(f"/api/workspace/members/{aid}", json={"status": "active"}, headers=owner)
    assert back.status_code == 409 and "at most 3" in back.json()["detail"]


def test_instance_limit_is_two_per_workspace(client, team):
    owner = team["owner"]
    assert connect(client, owner, "UAT", "uat-one").status_code == 201
    third = connect(client, owner, "Prod", "prod-one", "Production")
    assert third.status_code == 409 and "at most 2 ServiceNow instances" in third.json()["detail"]
    client.delete(f"/api/instances/{team['dev_org']['id']}", headers=owner)
    assert connect(client, owner, "Prod", "prod-one", "Production").status_code == 201


def test_roles_are_checked_on_the_server(client, team):
    owner = team["owner"]
    viewer = join(client, owner, "v@example.com", "viewer")
    assert client.post("/api/chats", headers=viewer).status_code == 403
    assert connect(client, viewer, "UAT", "uat-one").status_code == 403
    r = client.put("/api/settings/ai-provider", json={"model": "m", "api_key": "sk-ant-x123456789"}, headers=viewer)
    assert r.status_code == 403 and "admins" in r.json()["detail"]
    assert client.get("/api/settings/ai-provider", headers=viewer).status_code == 200  # shared provider is visible
    assert invite(client, viewer, "z@example.com", "viewer").status_code == 403
    assert client.get("/api/workspace/members", headers=viewer).json()["invites"] == []


def test_per_instance_access_hides_other_instances_and_their_chats(client, team):
    owner = team["owner"]
    uat = connect(client, owner, "UAT", "uat-one").json()
    client.post(f"/api/instances/{team['dev_org']['id']}/select", headers=owner)
    dev_chat = client.post("/api/chats", headers=owner).json()
    client.post(f"/api/instances/{uat['id']}/select", headers=owner)
    client.post("/api/chats", headers=owner)  # a chat on UAT
    asha = join(client, owner, "asha@example.com", "developer", instance_ids=[team["dev_org"]["id"]])
    assert [o["name"] for o in client.get("/api/instances", headers=asha).json()] == ["Dev"]
    assert [c["id"] for c in client.get("/api/chats", headers=asha).json()] == [dev_chat["id"]]
    assert client.post(f"/api/instances/{uat['id']}/select", headers=asha).status_code == 404
    # the owner widens access
    mid = next(m["id"] for m in client.get("/api/workspace/members", headers=owner).json()["members"] if m["email"] == "asha@example.com")
    client.patch(f"/api/workspace/members/{mid}", json={"all_instances": True}, headers=owner)
    assert len(client.get("/api/chats", headers=asha).json()) == 2
    # removing an org drops it from restricted members
    client.patch(f"/api/workspace/members/{mid}", json={"instance_ids": [uat["id"]]}, headers=owner)
    client.delete(f"/api/instances/{uat['id']}", headers=owner)
    assert client.get("/api/instances", headers=asha).json() == []


def test_owner_cannot_be_changed_and_admins_only_by_owner(client, team):
    owner = team["owner"]
    adm = join(client, owner, "a@example.com", "admin")
    members = client.get("/api/workspace/members", headers=owner).json()["members"]
    oid = next(m["id"] for m in members if m["role"] == "owner")
    r = client.patch(f"/api/workspace/members/{oid}", json={"role": "viewer"}, headers=adm)
    assert r.status_code == 403
    assert invite(client, adm, "x@example.com", "admin").status_code == 403  # only the owner invites admins
    assert invite(client, adm, "x@example.com", "developer").status_code == 201


def test_same_person_can_reuse_an_instance_name_in_another_workspace(client, team):
    # Vasu connected "Dev" in his own workspace; he joins Bo's workspace as admin and connects an org named "Dev" there
    bo = register(client, "bo@example.com", "Bo")
    r = invite(client, bo, "vasu@example.com", "admin")
    token = r.json()["link"].rsplit("/", 1)[1]
    assert client.post(f"/api/invites/{token}/accept", headers=team["owner"]).status_code == 200
    again = connect(client, team["owner"], "Dev", "dev-nine")
    assert again.status_code == 201, again.text
    dup = connect(client, bo, "Dev", "dev-ten")
    assert dup.status_code == 409 and "already has an instance named 'Dev'" in dup.json()["detail"]
