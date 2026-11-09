import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings

log = logging.getLogger("nowbuilder")
_ALGO = "HS256"
_DEV_FERNET_KEY: bytes | None = None


# ---------- passwords ----------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:  # an account without a password can't sign in with one
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# ---------- access tokens ----------

def create_access_token(user_id: str, version: int = 0) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": user_id, "ver": version, "iat": now, "exp": now + timedelta(minutes=s.access_token_minutes)}
    return jwt.encode(payload, s.secret_key, algorithm=_ALGO)


def decode_access_token(token: str) -> str | None:
    claims = decode_claims(token)
    return claims["sub"] if claims else None


def decode_claims(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None


# ---------- secrets at rest ----------

ENV_FILE = Path(".env")


class SecretUnreadable(RuntimeError):
    """A stored secret can't be decrypted (the encryption key changed)."""


class BadEncryptionKey(RuntimeError):
    pass


def _dev_key() -> bytes:
    """In development, create NOWBUILDER_ENCRYPTION_KEY once and save it to .env so restarts keep working."""
    global _DEV_FERNET_KEY
    if _DEV_FERNET_KEY is None:
        _DEV_FERNET_KEY = Fernet.generate_key()
        try:
            existing = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
            lines = [ln for ln in existing.splitlines() if not ln.startswith("NOWBUILDER_ENCRYPTION_KEY=")]
            lines.append(f"NOWBUILDER_ENCRYPTION_KEY={_DEV_FERNET_KEY.decode()}")
            ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
            log.warning("No NOWBUILDER_ENCRYPTION_KEY was set. Generated one and saved it to %s.", ENV_FILE.resolve())
        except OSError:
            log.warning("Couldn't save the generated encryption key to .env; saved secrets won't survive a restart.")
    return _DEV_FERNET_KEY


def _as_fernet_key(key: str) -> bytes:
    """A Fernet key (URL-safe base64 of 32 bytes), or any base64 of 32 random bytes, e.g. one a host generated."""
    import base64
    import binascii
    try:
        raw = base64.urlsafe_b64decode(key.encode())
    except (binascii.Error, ValueError):
        raw = b""
    if len(raw) != 32:
        try:
            raw = base64.b64decode(key.encode(), validate=True)
        except (binascii.Error, ValueError):
            raw = b""
    if len(raw) != 32:
        raise ValueError("not a 32-byte key")
    return base64.urlsafe_b64encode(raw)


def _fernet() -> Fernet:
    s = get_settings()
    key = s.encryption_key.strip()
    if key and not key.startswith("generate-"):
        try:
            return Fernet(_as_fernet_key(key))
        except ValueError as e:
            raise BadEncryptionKey("NOWBUILDER_ENCRYPTION_KEY in backend/.env isn't a valid key. Run `python -m app.keys` and paste the new value.") from e
    if s.environment != "development":
        raise BadEncryptionKey("NOWBUILDER_ENCRYPTION_KEY must be set outside development.")
    return Fernet(_dev_key())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as e:
        raise SecretUnreadable(
            "A saved secret can't be read because the encryption key changed. Re-enter your API key in "
            "Settings → AI provider and reconnect your instance in Settings → ServiceNow instances."
        ) from e
