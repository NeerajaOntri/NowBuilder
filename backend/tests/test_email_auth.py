"""Email (22 Oct): a 6-digit code confirms the email before anything works; forgot password sends a
one-time reset link; invites, new sign-ups and approvals send emails. In tests (like development
without an SMTP server) emails land in the dev outbox."""
import re
from datetime import UTC, timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AuthToken, User
from app.services import mailer

ADMIN = "vasu@example.com"


@pytest.fixture
def mail(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "require_email_verification", True)
    monkeypatch.setattr(s, "platform_admins", ADMIN)
    monkeypatch.setattr(s, "signup_mode", "approval")
    monkeypatch.setattr(mailer, "send_later", mailer.send)  # background emails sent at once in tests
    mailer.clear_outbox()
    return mailer


def sign_up(client, email, first="Ana"):
    r = client.post("/api/auth/register", json={"first_name": first, "last_name": "K", "email": email, "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


def emails(to=None, kind=None):
    return [m for m in mailer.outbox() if (to is None or m["to"] == to) and (kind is None or m["kind"] == kind)]


def code_for(email):
    return re.search(r"\b(\d{6})\b", emails(email, "verify")[0]["subject"]).group(1)


def verify(client, h, email):
    r = client.post("/api/auth/verify", json={"code": code_for(email)}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _age(purpose, user_email, minutes):
    """Make this person's tokens look older."""
    with SessionLocal() as db:
        uid = db.scalar(select(User.id).where(User.email == user_email))
        for t in db.scalars(select(AuthToken).where(AuthToken.user_id == uid, AuthToken.purpose == purpose)):
            t.created_at = t.created_at.replace(tzinfo=UTC) - timedelta(minutes=minutes)
            t.expires_at = t.expires_at.replace(tzinfo=UTC) - timedelta(minutes=minutes)
        db.commit()


def test_sign_up_needs_the_emailed_code_before_anything_works(client, mail):
    h, user = sign_up(client, "ana@acme.com")
    assert user["email_verified"] is False
    m = emails("ana@acme.com", "verify")
    assert len(m) == 1 and "is your nowBuilder code" in m[0]["subject"] and code_for("ana@acme.com") in m[0]["html"]
    blocked = client.get("/api/instances", headers=h)
    assert blocked.status_code == 403 and blocked.json()["code"] == "unverified"
    st = client.get("/api/auth/verify", headers=h).json()
    assert st["email"] == "ana@acme.com" and st["verified"] is False and 55 <= st["resend_in"] <= 60 and st["dev_outbox"] is True
    # wrong code: counted, plain message
    wrong = client.post("/api/auth/verify", json={"code": "000000" if code_for("ana@acme.com") != "000000" else "111111"}, headers=h)
    assert wrong.status_code == 400 and "4 tries left" in wrong.json()["detail"]
    me = verify(client, h, "ana@acme.com")
    assert me["email_verified"] is True
    # now it waits for the platform admin's approval
    assert client.get("/api/instances", headers=h).json()["code"] == "pending"


def test_codes_expire_allow_five_tries_and_resend_is_limited(client, mail):
    h, _ = sign_up(client, "ana@acme.com")
    code = code_for("ana@acme.com")
    bad = "000000" if code != "000000" else "111111"
    for _ in range(4):
        client.post("/api/auth/verify", json={"code": bad}, headers=h)
    last = client.post("/api/auth/verify", json={"code": bad}, headers=h)
    assert "last try" in last.json()["detail"]
    assert "Too many wrong tries" in client.post("/api/auth/verify", json={"code": code}, headers=h).json()["detail"]
    # a new code needs a minute's wait
    r = client.post("/api/auth/verify/resend", headers=h)
    assert r.status_code == 429 and "seconds" in r.json()["detail"]
    _age("verify", "ana@acme.com", 2)
    assert client.post("/api/auth/verify/resend", headers=h).json() == {"sent": True, "resend_in": 60}
    new = re.search(r"\b(\d{6})\b", emails("ana@acme.com", "verify")[-1]["subject"]).group(1)
    # the old code doesn't work any more; an expired code doesn't either
    _age("verify", "ana@acme.com", 11)
    r = client.post("/api/auth/verify", json={"code": new}, headers=h)
    assert r.status_code == 400 and "expired" in r.json()["detail"]
    # at most 5 codes an hour
    for _ in range(3):
        _age("verify", "ana@acme.com", 2)
        client.post("/api/auth/verify/resend", headers=h)
    assert client.post("/api/auth/verify/resend", headers=h).status_code == 429


def test_platform_admin_rights_and_the_platform_list_need_a_confirmed_email(client, mail):
    impostor, _ = sign_up(client, ADMIN, "Fake")
    assert client.get("/api/auth/me", headers=impostor).json()["is_platform_admin"] is False
    assert client.get("/api/platform/workspaces", headers=impostor).status_code == 403
    verify(client, impostor, ADMIN)  # whoever controls the inbox
    assert client.get("/api/auth/me", headers=impostor).json()["is_platform_admin"] is True
    assert client.get("/api/workspace", headers=impostor).status_code == 200 and emails(ADMIN, "approval-needed") == []
    admin = impostor
    h, _ = sign_up(client, "ana@acme.com")
    names = [w["owner"]["email"] for w in client.get("/api/platform/workspaces", headers=admin).json()["workspaces"]]
    assert "ana@acme.com" not in names  # unconfirmed sign-ups don't show
    verify(client, h, "ana@acme.com")
    data = client.get("/api/platform/workspaces", headers=admin).json()
    ws = next(w for w in data["workspaces"] if w["owner"]["email"] == "ana@acme.com")
    # the platform admins were told
    told = emails(ADMIN, "approval-needed")
    assert len(told) == 1 and "Ana K is waiting for approval" in told[0]["subject"] and "/platform" in told[0]["text"]
    # approving emails the owner
    client.patch(f"/api/platform/workspaces/{ws['id']}", json={"status": "active", "plan": "starter"}, headers=admin)
    ok = emails("ana@acme.com", "approved")
    assert len(ok) == 1 and "is approved" in ok[0]["subject"] and "up to 1 ServiceNow instance and" in ok[0]["text"]


def test_invites_are_emailed_and_invited_people_confirm_before_joining(client, mail):
    admin, _ = sign_up(client, ADMIN, "Vasu")
    verify(client, admin, ADMIN)
    r = client.post("/api/workspace/invites", json={"email": "dev@acme.com", "role": "developer"}, headers=admin)
    assert r.status_code == 201 and r.json()["emailed"] is True
    inv = emails("dev@acme.com", "invite")
    assert len(inv) == 1 and "invited you to Vasu's workspace" in inv[0]["subject"] and r.json()["link"] in inv[0]["text"]
    token = r.json()["link"].rsplit("/", 1)[1]
    h, _ = sign_up(client, "dev@acme.com", "Dev")
    r = client.post(f"/api/invites/{token}/accept", headers=h)
    assert r.status_code == 403 and r.json()["code"] == "unverified"
    verify(client, h, "dev@acme.com")
    assert emails(ADMIN, "approval-needed") == []  # invited into a team: nothing to approve
    assert client.post(f"/api/invites/{token}/accept", headers=h).status_code == 200


def test_forgot_password_sends_a_one_time_link_and_signs_out_old_sessions(client, mail):
    h, _ = sign_up(client, "ana@acme.com")
    # same answer whether or not the email has an account
    a = client.post("/api/auth/forgot", json={"email": "nobody@acme.com"}).json()
    b = client.post("/api/auth/forgot", json={"email": "ANA@acme.com"}).json()
    assert a == b and "If there's a nowBuilder account" in a["message"]
    assert emails("nobody@acme.com") == []
    link = re.search(r"(http\S+reset-password\?token=\S+)", emails("ana@acme.com", "reset")[0]["text"]).group(1)
    token = link.split("token=")[1]
    # a second request within a minute sends nothing new
    client.post("/api/auth/forgot", json={"email": "ana@acme.com"})
    assert len(emails("ana@acme.com", "reset")) == 1
    assert client.get(f"/api/auth/reset/{token}").json() == {"email": "ana@acme.com"}
    assert client.post("/api/auth/reset", json={"token": token, "password": "short"}).status_code == 422
    r = client.post("/api/auth/reset", json={"token": token, "password": "new-secret-1"})
    assert r.status_code == 200 and "Sign in with the new password" in r.json()["message"]
    # the old session is signed out, the old password doesn't work, the new one does
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ana@acme.com", "password": "secret123"}).status_code == 401
    new = client.post("/api/auth/login", json={"email": "ana@acme.com", "password": "new-secret-1"})
    assert new.status_code == 200 and new.json()["user"]["email_verified"] is True  # the link proved the address
    nh = {"Authorization": f"Bearer {new.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=nh).status_code == 200
    # the link works once
    again = client.post("/api/auth/reset", json={"token": token, "password": "another-pass"})
    assert again.status_code == 400 and "already been used" in again.json()["detail"]


def test_reset_links_expire(client, mail):
    sign_up(client, "ana@acme.com")
    client.post("/api/auth/forgot", json={"email": "ana@acme.com"})
    token = re.search(r"token=(\S+)", emails("ana@acme.com", "reset")[0]["text"]).group(1)
    _age("reset", "ana@acme.com", 31)
    r = client.get(f"/api/auth/reset/{token}")
    assert r.status_code == 400 and "expired" in r.json()["detail"]


def test_without_a_mail_server_hosted_mail_fails_with_a_clear_message(client, mail, monkeypatch):
    monkeypatch.setattr(get_settings(), "environment", "production")
    monkeypatch.setattr(get_settings(), "smtp_host", "")
    h, _ = sign_up(client, "ana@acme.com")  # the account is still created
    _age("verify", "ana@acme.com", 2)
    r = client.post("/api/auth/verify/resend", headers=h)
    assert r.status_code == 502 and "no mail settings" in r.json()["detail"]
    assert client.get("/api/auth/dev-outbox").status_code == 404  # never exposed outside development


def test_smtp_settings_are_used(client, mail, monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["server"] = (host, port)
        def starttls(self, context):  # noqa: ARG002
            sent["tls"] = True
        def login(self, user, password):
            sent["login"] = user
        def send_message(self, msg, from_addr=None):
            sent["to"], sent["from"], sent["subject"] = msg["To"], msg["From"], msg["Subject"]
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    s = get_settings()
    for k, v in {"smtp_host": "smtp.example.com", "smtp_port": 587, "smtp_user": "apikey", "smtp_password": "x",
                 "mail_from": "nowBuilder <no-reply@nowbuilder.dev>"}.items():
        monkeypatch.setattr(s, k, v)
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    sign_up(client, "ana@acme.com")
    assert sent == {"server": ("smtp.example.com", 587), "tls": True, "login": "apikey", "to": "ana@acme.com",
                    "from": "nowBuilder <no-reply@nowbuilder.dev>", "subject": sent["subject"]}
    assert sent["subject"].endswith("is your nowBuilder code") and mailer.outbox() == []


def test_mail_errors_say_what_to_fix(monkeypatch):
    import smtplib
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", "smtp.gmail.com")
    monkeypatch.setattr(s, "smtp_user", "")
    refused = smtplib.SMTPSenderRefused(530, b"5.7.0 Authentication Required.", "no-reply@nowbuilder.local")
    msg = mailer.explain(refused)
    assert "530 5.7.0 Authentication Required" in msg and "NOWBUILDER_SMTP_USER is empty" in msg
    monkeypatch.setattr(s, "smtp_user", "nowbuilder.notify@gmail.com")
    assert "App password" in mailer.explain(smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted"))
    monkeypatch.setattr(s, "smtp_host", "smtp.office365.com")
    ms = mailer.explain(smtplib.SMTPAuthenticationError(535, b"5.7.139 Authentication unsuccessful, SmtpClientAuthentication is disabled for the Tenant."))
    assert "IT admin" in ms and "Gmail" in ms
    monkeypatch.setattr(s, "smtp_host", "smtp.gmail.com")
    assert "nowBuilder <nowbuilder.notify@gmail.com>" in mailer.explain(refused)


def test_envelope_sender_is_the_signed_in_account(client, monkeypatch):
    seen = {}

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def starttls(self, context): pass
        def login(self, user, password): seen["login"] = (user, password)
        def send_message(self, msg, from_addr=None): seen["envelope"], seen["from"] = from_addr, msg["From"]
        def __enter__(self): return self
        def __exit__(self, *a): return False
    s = get_settings()
    for k, v in {"smtp_host": "smtp.gmail.com", "smtp_user": "nowbuilder.notify@gmail.com", "smtp_password": "abcd efgh ijkl mnop",
                 "mail_from": "nowBuilder <no-reply@nowbuilder.local>"}.items():
        monkeypatch.setattr(s, k, v)
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    mailer.send(mailer.Mail(to="a@b.co", subject="x", text="x", html="x"))
    assert seen == {"login": ("nowbuilder.notify@gmail.com", "abcdefghijklmnop"), "envelope": "nowbuilder.notify@gmail.com",
                    "from": "nowBuilder <no-reply@nowbuilder.local>"}
