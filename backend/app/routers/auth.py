"""Accounts: sign up, sign in, email verification code, forgot / reset password (22 Oct 2026)."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from ..config import get_settings
from ..deps import DB, CurrentUser
from ..models import AuthToken, User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services import mailer

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Same cost as a real check, so response time doesn't reveal whether an email is registered
_DUMMY_HASH = hash_password("not-a-real-password")

CODE_MINUTES = 10          # a sign-up code works this long
CODE_ATTEMPTS = 5          # wrong tries per code, then a new code is needed
RESEND_SECONDS = 60        # wait between codes / reset emails
SENDS_PER_HOUR = 5         # codes or reset emails per account per hour
RESET_MINUTES = 30         # a reset link works this long, once
FORGOT_REPLY = "If there's a nowBuilder account for that email, we've sent a link to reset the password. It works for 30 minutes."


class VerifyIn(BaseModel):
    code: str = Field(min_length=1, max_length=12)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=200)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id, user.session_version or 0), user=UserOut.model_validate(user))


def _recent(db, user: User, purpose: str) -> list[AuthToken]:
    since = _now() - timedelta(hours=1)
    return [t for t in db.scalars(select(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose)
                                  .order_by(AuthToken.created_at.desc())) if _aware(t.created_at) > since]


def _wait_seconds(db, user: User, purpose: str) -> int:
    """How long before another code / reset email can go to this person (0 = now)."""
    recent = _recent(db, user, purpose)
    if len(recent) >= SENDS_PER_HOUR:
        return max(1, int((_aware(recent[-1].created_at) + timedelta(hours=1) - _now()).total_seconds()))
    if recent:
        return max(0, int((_aware(recent[0].created_at) + timedelta(seconds=RESEND_SECONDS) - _now()).total_seconds()))
    return 0


def _send_code(db, user: User) -> None:
    for old in db.scalars(select(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == "verify", AuthToken.used_at.is_(None))):
        old.used_at = _now()  # one live code at a time
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(AuthToken(user_id=user.id, purpose="verify", secret_hash=_hash(code), expires_at=_now() + timedelta(minutes=CODE_MINUTES)))
    db.commit()
    mailer.send(mailer.verification_code(user.email, user.first_name, code, CODE_MINUTES))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DB) -> TokenOut:
    email = body.email.lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Sign in instead.")
    user = User(email=email, first_name=body.first_name, last_name=body.last_name, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    # their own workspace now, so a platform admin sees the sign-up straight away (pending with approval sign-up)
    from ..services.workspace import ensure_membership
    ensure_membership(db, user)
    if get_settings().require_email_verification:
        try:
            _send_code(db, user)
        except mailer.MailError:
            pass  # the account exists; the verify page offers "Send a new code" and shows the problem there
    else:
        _after_verified(db, user)
    return _token(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DB) -> TokenOut:
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if not verify_password(body.password, user.password_hash if user else _DUMMY_HASH) or not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


# ---------- email verification ----------

@router.get("/verify")
def verify_status(user: CurrentUser, db: DB) -> dict:
    """For the verify page: where the code went and when another can be sent."""
    return {"email": user.email, "verified": user.email_verified, "resend_in": _wait_seconds(db, user, "verify"),
            "dev_outbox": get_settings().dev_outbox}


@router.post("/verify", response_model=UserOut)
def verify(body: VerifyIn, user: CurrentUser, db: DB) -> User:
    if user.email_verified_at is not None:
        return user
    code = "".join(ch for ch in body.code if ch.isdigit())
    t = db.scalar(select(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == "verify", AuthToken.used_at.is_(None))
                  .order_by(AuthToken.created_at.desc()))
    if t is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That code isn't valid any more. Send a new code.")
    if _aware(t.expires_at) <= _now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"That code has expired (codes work for {CODE_MINUTES} minutes). Send a new code.")
    if t.attempts >= CODE_ATTEMPTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many wrong tries for this code. Send a new code.")
    if not secrets.compare_digest(_hash(code), t.secret_hash):
        t.attempts += 1
        db.commit()
        left = CODE_ATTEMPTS - t.attempts
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"That code isn't right. {left} {'try' if left == 1 else 'tries'} left." if left
                            else "That code isn't right, and that was the last try. Send a new code.")
    t.used_at = user.email_verified_at = _now()
    db.commit()
    _after_verified(db, user)
    return user


@router.post("/verify/resend")
def resend(user: CurrentUser, db: DB) -> dict:
    if user.email_verified_at is not None:
        return {"sent": False, "resend_in": 0}
    wait = _wait_seconds(db, user, "verify")
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"You can ask for a new code in {wait} seconds.")
    try:
        _send_code(db, user)
    except mailer.MailError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    return {"sent": True, "resend_in": RESEND_SECONDS}


def _after_verified(db, user: User) -> None:
    """Tell the platform admins a workspace is waiting, unless the person was invited into a team."""
    from ..models import Invite, Membership, PlatformAdmin, Workspace
    m = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.status == "active"))
    ws = db.get(Workspace, m.workspace_id) if m else None
    if ws is None or ws.status != "pending":
        return
    if user.is_platform_admin:  # a platform admin's own workspace never waits
        ws.status = "active"
        db.commit()
        return
    invited = db.scalar(select(Invite.id).where(func.lower(Invite.email) == user.email.lower(), Invite.status == "pending"))
    if invited:
        return
    admins = get_settings().platform_admin_emails | set(db.scalars(select(PlatformAdmin.email)))
    url = f"{get_settings().public_url.rstrip('/')}/platform"
    for email in sorted(admins):
        mailer.send_later(mailer.signup_waiting(email, f"{user.first_name} {user.last_name}".strip(), user.email, ws.name, url))


# ---------- forgot / reset password ----------

@router.post("/forgot")
def forgot(body: ForgotIn, db: DB) -> dict:
    """Always the same answer, so the page doesn't tell anyone which emails have accounts."""
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is None or _wait_seconds(db, user, "reset"):
        return {"message": FORGOT_REPLY}
    for old in db.scalars(select(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == "reset", AuthToken.used_at.is_(None))):
        old.used_at = _now()  # only the newest link works
    token = secrets.token_urlsafe(32)
    db.add(AuthToken(user_id=user.id, purpose="reset", secret_hash=_hash(token), expires_at=_now() + timedelta(minutes=RESET_MINUTES)))
    db.commit()
    url = f"{get_settings().public_url.rstrip('/')}/reset-password?token={token}"
    try:
        mailer.send(mailer.password_reset(user.email, user.first_name, url, RESET_MINUTES))
    except mailer.MailError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    return {"message": FORGOT_REPLY}


def _reset_token(db, token: str) -> AuthToken:
    t = db.scalar(select(AuthToken).where(AuthToken.secret_hash == _hash(token), AuthToken.purpose == "reset"))
    if t is None or t.used_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link has already been used or isn't valid. Ask for a new one.")
    if _aware(t.expires_at) <= _now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This reset link has expired (links work for {RESET_MINUTES} minutes). Ask for a new one.")
    return t


@router.get("/reset/{token}")
def check_reset(token: str, db: DB) -> dict:
    """For the reset page: is the link still good, and for which account."""
    t = _reset_token(db, token)
    user = db.get(User, t.user_id)
    return {"email": user.email if user else ""}


@router.post("/reset")
def reset(body: ResetIn, db: DB) -> dict:
    t = _reset_token(db, body.token)
    user = db.get(User, t.user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link isn't valid. Ask for a new one.")
    user.password_hash = hash_password(body.password)
    user.password_changed_at = t.used_at = _now()
    user.session_version = (user.session_version or 0) + 1  # every earlier session is signed out
    if user.email_verified_at is None:  # they opened a link sent to that address
        user.email_verified_at = _now()
    db.commit()
    return {"message": "Your password is changed. Sign in with the new password."}


# ---------- development: emails that would have been sent ----------

@router.get("/dev-outbox")
def dev_outbox() -> dict:
    if not get_settings().dev_outbox:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return {"emails": mailer.outbox()}
