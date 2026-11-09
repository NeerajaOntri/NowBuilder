"""Platform page (platform admins only): every workspace, its plan, limits and status."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ..config import get_settings
from ..deps import DB, CurrentUser
from ..models import User, Workspace
from ..services import platform

router = APIRouter(prefix="/api/platform", tags=["platform"])

KEEP = "keep"


class WorkspaceUpdate(BaseModel):
    plan: str | None = None
    # null = use the plan's number; leave out to keep what's there
    max_instances: int | None = Field(default=None, ge=1, le=platform.MAX_LIMIT)
    max_members: int | None = Field(default=None, ge=1, le=platform.MAX_LIMIT)
    status: str | None = None
    note: str | None = Field(default=None, max_length=500)


class AdminIn(BaseModel):
    email: EmailStr


class DeleteIn(BaseModel):
    confirm: str = Field(max_length=200)


def _admin(user: User) -> User:
    if not user.is_platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only nowBuilder platform admins can open the Platform page.")
    return user


def _overview(db) -> dict:
    rows = platform.list_workspaces(db)
    s = get_settings()
    return {"workspaces": rows, "counts": platform.counts(rows), "plans": platform.plans(),
            "signup": "approval" if s.signup_needs_approval else "open"}


@router.get("/workspaces")
def list_workspaces(user: CurrentUser, db: DB) -> dict:
    _admin(user)
    return _overview(db)


@router.patch("/workspaces/{workspace_id}")
def update_workspace(workspace_id: str, body: WorkspaceUpdate, user: CurrentUser, db: DB) -> dict:
    _admin(user)
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That workspace doesn't exist any more.")
    sent = body.model_fields_set
    try:
        platform.update_workspace(db, user, ws, plan=body.plan,
                                  max_instances=body.max_instances if "max_instances" in sent else KEEP,
                                  max_members=body.max_members if "max_members" in sent else KEEP,
                                  status=body.status, note=body.note)
    except platform.PlatformError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return {**_overview(db), "workspace": platform.workspace_row(db, ws)}


@router.get("/summary")
def summary(user: CurrentUser, db: DB) -> dict:
    """For the top bar: how many workspaces wait for approval."""
    _admin(user)
    return {"pending": platform.counts(platform.list_workspaces(db))["pending"]}


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, body: DeleteIn, user: CurrentUser, db: DB) -> dict:
    _admin(user)
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That workspace doesn't exist any more.")
    try:
        name = platform.delete_workspace(db, user, ws, body.confirm)
    except platform.PlatformError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return {**_overview(db), "deleted": name}


@router.get("/admins")
def list_admins(user: CurrentUser, db: DB) -> dict:
    _admin(user)
    return {"admins": platform.admins(db, user)}


@router.post("/admins", status_code=status.HTTP_201_CREATED)
def add_admin(body: AdminIn, user: CurrentUser, db: DB) -> dict:
    _admin(user)
    try:
        platform.add_admin(db, user, body.email)
    except platform.PlatformError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return {"admins": platform.admins(db, user)}


@router.delete("/admins/{email}")
def remove_admin(email: str, user: CurrentUser, db: DB) -> dict:
    _admin(user)
    try:
        platform.remove_admin(db, user, email)
    except platform.PlatformError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return {"admins": platform.admins(db, user)}
