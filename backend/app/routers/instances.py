"""Settings → ServiceNow instances (Chunk 1): connect, check, rename, update the sign-in, select, remove."""
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from ..deps import DB, WorkspaceCtx
from ..models import Instance
from ..schemas import InstanceCreateIn, InstanceOut, InstanceUpdateIn
from ..security import encrypt
from pydantic import BaseModel, Field

from ..services import servicenow, workspace
from ..services.servicenow import ServiceNowClient, ServiceNowError
from ..services.workspace import Ctx

router = APIRouter(prefix="/api/instances", tags=["servicenow instances"])


def make_client(instance: Instance, db=None) -> ServiceNowClient:  # swapped in tests for a fake instance
    return ServiceNowClient(instance, db)


def oauth_tokens(url: str, client_id: str, client_secret: str, username: str, password: str) -> dict:  # swapped in tests
    return servicenow.oauth_password_grant(url, client_id, client_secret, username, password)


def _auto_deploy_default(asked: bool | None) -> bool:
    from ..config import get_settings
    return get_settings().auto_deploy if asked is None else asked


def _prepare_sdk(inst: Instance, password: str) -> None:
    """Start the one-time ServiceNow SDK setup for flows in the background, so the first flow
    doesn't wait for the npm download. Never on Production; never blocks or fails the request."""
    if inst.instance_type == "Production" or not password:
        return
    try:
        from ..services import sdk_deploy
        sdk_deploy.start_setup(inst.url, inst.username, password, make_client(inst))
    except Exception:  # noqa: BLE001 — flows report SDK problems when they deploy
        pass


def _get(ctx: Ctx, instance_id: str) -> Instance:
    inst = ctx.instance(instance_id)
    if not inst:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instance not found.")
    return inst


def _out(ctx: Ctx, inst: Instance) -> InstanceOut:
    sel = ctx.selected_instance()
    return InstanceOut.model_validate(inst).model_copy(update={"is_selected": sel is not None and sel.id == inst.id})


def _check(inst: Instance, db) -> None:
    """Sign in and read who we are; raises ServiceNowError with a plain message."""
    info = make_client(inst, db).whoami()
    if not info.user_sys_id:
        raise ServiceNowError(f"Signed in, but couldn't read the user {inst.username}. Give it read access to users (sys_user), or use an admin account.")
    inst.release, inst.user_sys_id, inst.user_display_name = info.release, info.user_sys_id, info.user_display_name
    inst.roles, inst.is_admin = info.roles, info.is_admin
    inst.status, inst.status_message, inst.last_checked_at = "connected", None, datetime.now(UTC)
    if not info.is_admin:
        inst.status_message = ("Connected. This user doesn't have the admin role, so nowBuilder can read the instance "
                               "but won't be able to create business rules and scripts until it does.")


def _sign_in(inst: Instance, password: str, client_secret: str | None) -> None:
    inst.password_enc = encrypt(password)
    if inst.auth_method == "oauth":
        if not inst.client_id or not client_secret:
            raise ServiceNowError("OAuth needs the client id and client secret from System OAuth → Application Registry.")
        inst.client_secret_enc = encrypt(client_secret)
        servicenow.save_tokens(inst, oauth_tokens(inst.url, inst.client_id, client_secret, inst.username, password))


@router.get("/defaults")
def defaults(ctx: WorkspaceCtx) -> dict:
    """What the connect form starts with: the instance nowBuilder is set up for."""
    from ..config import get_settings
    st = get_settings()
    return {"url": st.default_instance_url, "auto_deploy": st.auto_deploy}


@router.get("", response_model=list[InstanceOut])
def list_instances(ctx: WorkspaceCtx) -> list[InstanceOut]:
    return [_out(ctx, i) for i in ctx.instances()]


@router.post("", response_model=InstanceOut, status_code=status.HTTP_201_CREATED)
def connect(body: InstanceCreateIn, ctx: WorkspaceCtx, db: DB) -> InstanceOut:
    ctx.require("manage_instances")
    try:
        url = servicenow.normalise_url(body.url)
    except ServiceNowError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    name = body.name.strip()
    if any(i.name == name for i in ctx.all_instances()):
        raise HTTPException(status.HTTP_409_CONFLICT, f"This workspace already has an instance named '{name}'.")
    if any(i.url == url for i in ctx.all_instances()):
        raise HTTPException(status.HTTP_409_CONFLICT, f"{url} is already connected.")
    workspace.check_instance_room(ctx)
    inst = Instance(user_id=ctx.user.id, workspace_id=ctx.workspace.id, name=name, instance_type=body.instance_type, url=url,
                    auth_method=body.auth_method, username=body.username.strip(), client_id=body.client_id.strip(),
                    auto_deploy=_auto_deploy_default(body.auto_deploy) and body.instance_type != "Production")
    try:
        _sign_in(inst, body.password, body.client_secret)
        _check(inst, None)
    except ServiceNowError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    db.add(inst)
    db.flush()
    if ctx.member.selected_instance_id is None or ctx.instance(ctx.member.selected_instance_id) is None:
        ctx.select_instance(inst)
    db.commit()
    _prepare_sdk(inst, body.password)
    return _out(ctx, inst)


@router.post("/{instance_id}/test", response_model=InstanceOut)
def test(instance_id: str, ctx: WorkspaceCtx, db: DB) -> InstanceOut:
    """Check the connection again (and refresh the user's roles and the release)."""
    inst = _get(ctx, instance_id)
    try:
        _check(inst, db)
    except ServiceNowError as e:
        inst.status, inst.status_message, inst.last_checked_at = "error", str(e), datetime.now(UTC)
    db.commit()
    if inst.status == "connected" and inst.password_enc:
        from ..security import decrypt
        _prepare_sdk(inst, decrypt(inst.password_enc))
    return _out(ctx, inst)


@router.patch("/{instance_id}", response_model=InstanceOut)
def update(instance_id: str, body: InstanceUpdateIn, ctx: WorkspaceCtx, db: DB) -> InstanceOut:
    ctx.require("manage_instances")
    inst = _get(ctx, instance_id)
    if body.name is not None:
        name = body.name.strip()
        if any(i.name == name and i.id != inst.id for i in ctx.all_instances()):
            raise HTTPException(status.HTTP_409_CONFLICT, f"This workspace already has an instance named '{name}'.")
        inst.name = name
    if body.instance_type is not None:
        inst.instance_type = body.instance_type
    if body.auto_deploy is not None:
        inst.auto_deploy = body.auto_deploy
    if inst.instance_type == "Production":
        inst.auto_deploy = False   # production always asks first
    signin_changed = any(v is not None for v in (body.username, body.password, body.client_id, body.client_secret))
    if signin_changed:
        if body.username is not None:
            inst.username = body.username.strip()
        if body.client_id is not None:
            inst.client_id = body.client_id.strip()
        if body.password is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter the password to save new sign-in details.")
        from ..security import decrypt
        secret = body.client_secret or (decrypt(inst.client_secret_enc) if inst.client_secret_enc else None)
        try:
            inst.refresh_token_enc = inst.access_token_enc = ""
            _sign_in(inst, body.password, secret)
            _check(inst, db)
        except ServiceNowError as e:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    db.commit()
    return _out(ctx, inst)


@router.post("/{instance_id}/select", response_model=InstanceOut)
def select(instance_id: str, ctx: WorkspaceCtx, db: DB) -> InstanceOut:
    """Which instance this member works in (each member chooses their own)."""
    inst = _get(ctx, instance_id)
    ctx.select_instance(inst)
    db.commit()
    return _out(ctx, inst)


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(instance_id: str, ctx: WorkspaceCtx, db: DB) -> None:
    """Remove the connection from nowBuilder. Nothing in the instance changes."""
    ctx.require("manage_instances")
    inst = _get(ctx, instance_id)
    workspace.forget_instance(db, inst.id)
    db.delete(inst)
    db.commit()

@router.post("/{instance_id}/health")
def health_check(instance_id: str, ctx: WorkspaceCtx, db: DB) -> dict:
    """Best-practice scan of the instance's active custom scripts. Read-only."""
    from ..services import health
    inst = _get(ctx, instance_id)
    try:
        return {**health.scan(make_client(inst, db)), "instance": inst.url}
    except ServiceNowError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e


class PromoteIn(BaseModel):
    update_set_id: str = Field(min_length=32, max_length=32, pattern=r"^[0-9a-f]{32}$")
    target_instance_id: str
    confirm: bool = False


@router.post("/{instance_id}/promote")
def promote_update_set(instance_id: str, body: PromoteIn, ctx: WorkspaceCtx, db: DB) -> dict:
    """Preview (confirm=false) or copy (confirm=true) an update set into another connected instance as a
    retrieved update set, for its admin to preview and commit there."""
    from ..services import promote
    source = _get(ctx, instance_id)
    target = _get(ctx, body.target_instance_id)
    if target.id == source.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a different target instance.")
    try:
        if not body.confirm:
            return {**promote.preview(make_client(source, db), body.update_set_id), "target": target.url,
                    "target_type": target.instance_type}
        return promote.promote(make_client(source, db), make_client(target, db), body.update_set_id)
    except (promote.PromoteError, ServiceNowError) as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e


@router.get('/{instance_id}/deployment-readiness')
def deployment_readiness(instance_id: str, ctx: WorkspaceCtx, db: DB):
    """Read-only diagnostics for a connected instance; no credentials returned."""
    from ..services.deployment_readiness import assess
    inst = _get(ctx, instance_id)
    return assess(make_client(inst, db), inst, application_scope='global')
