from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_claims

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> User:
    claims = decode_claims(creds.credentials) if creds else None
    user = db.get(User, claims["sub"]) if claims else None
    if user and int(claims.get("ver", 0)) != (user.session_version or 0):  # signed out by a password reset
        user = None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.", headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def current_ctx(db: DB, user: CurrentUser):
    """The signed-in user in their workspace (creates their own workspace on first use)."""
    from .services.workspace import context
    return context(db, user)


from .services.workspace import Ctx as _Ctx  # noqa: E402

WorkspaceCtx = Annotated[_Ctx, Depends(current_ctx)]
