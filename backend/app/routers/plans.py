"""Plans: the cards in the chat, their checks, Fix with AI, and deploying into an update set.

Chunk 2 reads them, Chunk 3 checks and fixes them, Chunk 4 approves, deploys and rolls back.
The long-running ones (fix, deploy, rollback) stream progress as Server-Sent Events, like the chat.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..ai import checks, fixing
from ..ai.planning import plan_out
from ..ai.skills import get_skills
from ..db import SessionLocal
from ..deps import DB, WorkspaceCtx
from ..models import AIProviderConfig, Chat, FixProposal, Instance, Plan
from ..services import deploy as deploy_svc
from ..services.deploy import DeployError
from ..services.servicenow import ServiceNowClient, ServiceNowError
from ..services.workspace import Ctx
from ..ai import usage

router = APIRouter(prefix="/api", tags=["plans"])


# ---------- shared bits ----------

def _chats():
    """The chats router holds the model factory and the instance summary. Imported when needed,
    because it imports this module for a chat's plans; `chats.llm_factory` stays the swap point."""
    from . import chats
    return chats


def _get_plan(ctx: Ctx, db, plan_id: str, action: str | None = None) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None or not ctx.can_see_chat(db.get(Chat, plan.chat_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found.")
    if action:
        ctx.require(action)
    return plan


def plans_for_chat(db, chat: Chat) -> list[dict]:
    """A chat's plans, each with its fixes, so reopening the chat still shows a waiting proposal."""
    plans = db.scalars(select(Plan).where(Plan.chat_id == chat.id).order_by(Plan.created_at))
    return [{**plan_out(p), "fixes": _fix_proposals(db, p.id)} for p in plans]


def _instance(ctx: Ctx, plan: Plan) -> Instance | None:
    return ctx.instance(plan.instance_id) or ctx.selected_instance()


def _client(ctx: Ctx, inst: Instance | None) -> ServiceNowClient | None:
    return ServiceNowClient(inst, ctx.db) if inst else None


BUSY_STALE_MINUTES = 30   # longer than any build, fix or deploy; older marks were left by a stopped run


def _busy_guard(plan: Plan, db=None) -> None:
    if plan.busy and plan.busy_since is not None:
        since = plan.busy_since if plan.busy_since.tzinfo else plan.busy_since.replace(tzinfo=UTC)
        if (datetime.now(UTC) - since).total_seconds() > BUSY_STALE_MINUTES * 60:
            plan.busy = plan.busy_since = plan.progress = None
            if db is not None:
                db.commit()
            return
    if plan.busy:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This plan is already {plan.busy}. Wait for that to finish, "
                                                      f"or restart the backend if nothing is running.")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


def _fix_proposals(db, plan_id: str) -> list[dict]:
    rows = db.scalars(select(FixProposal).where(FixProposal.plan_id == plan_id).order_by(FixProposal.created_at))
    return [fixing.proposal_out(p) for p in rows]


def _full(db, plan: Plan) -> dict:
    return {**plan_out(plan), "fixes": _fix_proposals(db, plan.id)}


# ---------- reading ----------

@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, ctx: WorkspaceCtx, db: DB) -> dict:
    return _full(db, _get_plan(ctx, db, plan_id))


@router.get("/plans/{plan_id}/document")
def design_document(plan_id: str, ctx: WorkspaceCtx, db: DB):
    """The plan as a technical design document (.docx), built from the plan and its deployment."""
    from fastapi.responses import Response
    from ..services import design_doc
    plan = _get_plan(ctx, db, plan_id)
    data = _full(db, plan)
    inst = db.get(Instance, plan.instance_id) if getattr(plan, "instance_id", None) else None
    body = design_doc.build(data, inst.url if inst else "")
    safe = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in (plan.title or "design"))[:80].strip() or "design"
    return Response(body, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{safe} - design.docx"'})


# ---------- SDK source preview: never claims to deploy ----------
@router.get("/plans/{plan_id}/components/{component_id}/flow-source")
def flow_source(plan_id: str, component_id: str, ctx: WorkspaceCtx, db: DB):
    from fastapi.responses import PlainTextResponse
    from ..ai.flow_sdk import generate_flow_source, UnsupportedFlow
    plan = _get_plan(ctx, db, plan_id, "build")
    component = next((c for c in plan.components if c.get("id") == component_id), None)
    if not component or component.get("type") != "flow":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flow component not found.")
    try:
        src = generate_flow_source(component.get("generated") or {})
    except UnsupportedFlow as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return PlainTextResponse(src, headers={"X-NowBuilder-Deployment-Status": "source-only"})


# ---------- SDK local readiness (no deployment) ----------
@router.get('/sdk/readiness')
def sdk_readiness(ctx: WorkspaceCtx):
    from ..services.sdk_deploy import sdk_preflight, SDKDeployError
    try:
        return sdk_preflight()
    except (SDKDeployError, OSError, ValueError) as exc:
        return {'ready_for_local_build': False, 'reason': str(exc)}


# ---------- Optional SDK build/install for explicitly configured scoped applications ----------
class SDKFlowRequest(BaseModel):
    confirm_install: bool = False


@router.post("/plans/{plan_id}/components/{component_id}/sdk-build")
def sdk_flow_build(plan_id: str, component_id: str, body: SDKFlowRequest, ctx: WorkspaceCtx, db: DB):
    """Build a flow row with the ServiceNow SDK and, with confirm_install, install it into the plan's
    instance using that instance's sign-in. Rows it points at ({{plan.<id>}}) must be deployed first."""
    from sqlalchemy.orm.attributes import flag_modified

    from ..ai.flow_sdk import plan_refs, resolve_plan_refs
    from ..security import decrypt
    from ..services.sdk_deploy import SDKDeployError, read_back_flow, run_scoped_flow
    plan = _get_plan(ctx, db, plan_id, "build" if not body.confirm_install else None)
    _busy_guard(plan, db)
    component = next((c for c in plan.components if c.get("id") == component_id), None)
    if not component or component.get("type") != "flow":
        raise HTTPException(404, "Flow component not found.")
    inst = _instance(ctx, plan)
    generated = component.get("generated") or {}
    by_id = {c["id"]: c for c in plan.components}
    sys_ids = {r: (by_id.get(r, {}).get("deploy") or {}).get("sys_id") for r in plan_refs(generated)}
    generated = resolve_plan_refs(generated, {k: v for k, v in sys_ids.items() if v})
    creds: dict = {}
    if body.confirm_install:
        if inst is None:
            raise HTTPException(409, "Connect a ServiceNow instance before installing a flow.")
        ctx.require_deploy(inst)
        if inst.instance_type == "Production":
            raise HTTPException(409, "Install flows into production through your release process, not from nowBuilder.")
        creds = {"instance_url": inst.url, "username": inst.username,
                 "password": decrypt(inst.password_enc) if inst.password_enc else None,
                 "client": _client(ctx, inst)}
    try:
        out = run_scoped_flow(generated, install=body.confirm_install, **creds)
    except SDKDeployError as exc:
        raise HTTPException(422, str(exc)) from exc
    if body.confirm_install and inst is not None:
        found = read_back_flow(_client(ctx, inst), str((generated.get("record") or {}).get("name") or ""))
        component["deploy"] = ({"status": "deployed", "via": "sdk", "verified": True, **found}
                               if found else {"status": "verification failed", "via": "sdk",
                                              "message": "Installed, but the flow didn't come back from sys_hub_flow."})
        flag_modified(plan, "components")
        db.commit()
        out["deploy"] = component["deploy"]
    return out


# ---------- Chunk 3: checks ----------

@router.post("/plans/{plan_id}/check")
def recheck(plan_id: str, ctx: WorkspaceCtx, db: DB, es2021: bool = False) -> dict:
    """Run the checks again (after an edit, or when the instance has changed)."""
    plan = _get_plan(ctx, db, plan_id, "build")
    _busy_guard(plan, db)
    inst = _instance(ctx, plan)
    plan.validation = {**checks.run(plan.components, _client(ctx, inst), es2021=es2021,
                                    application=plan.application), "at": _now()}
    fixing.save(db, plan)
    return _full(db, plan)


# ---------- Chunk 3: Fix with AI ----------

class FixIn(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=fixing.MAX_ROWS_PER_FIX)


@router.post("/plans/{plan_id}/fix")
def fix_with_ai(plan_id: str, body: FixIn, ctx: WorkspaceCtx, db: DB) -> StreamingResponse:
    plan = _get_plan(ctx, db, plan_id, "build")
    _busy_guard(plan, db)
    ai_cfg = ctx.ai_config()
    if not ai_cfg or not ai_cfg.verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add and verify the workspace's AI provider in Settings → AI provider first.")
    inst = _instance(ctx, plan)
    llm = usage.metered(_chats().llm_factory(ai_cfg), ai_cfg, user_id=ctx.user.id, operation="fix", plan_id=plan.id)
    plan.busy, plan.busy_since = "fixing", datetime.now(UTC)
    db.commit()
    plan_id_s, instance_id, ids = plan.id, (inst.id if inst else None), list(body.ids)
    summary = _chats().instance_summary(inst) if inst else None

    def stream() -> Iterator[str]:
        sdb = SessionLocal()
        try:
            p = sdb.get(Plan, plan_id_s)
            inst_s = sdb.get(Instance, instance_id) if instance_id else None
            client = ServiceNowClient(inst_s, sdb) if inst_s else None
            events: list[dict] = []
            yield _sse({"type": "start", "plan_id": plan_id_s})
            result = fixing.propose(sdb, llm, get_skills(), p, ids, client, summary,
                                    on_status=lambda s: events.append({"type": "status", "text": s}))
            for e in events:
                yield _sse(e)
            p.busy, p.busy_since = None, None
            sdb.commit()
            if result.proposal is None:
                yield _sse({"type": "error", "message": result.message})
            else:
                yield _sse({"type": "fix", "fix": fixing.proposal_out(result.proposal), "plan": plan_out(p)})
            yield _sse({"type": "done"})
        except Exception:  # noqa: BLE001
            _release(plan_id_s)
            yield _sse({"type": "error", "message": "nowBuilder hit an unexpected problem while fixing. Try again."})
            raise
        finally:
            sdb.close()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _release(plan_id: str) -> None:
    db = SessionLocal()
    try:
        p = db.get(Plan, plan_id)
        if p is not None and p.busy:
            p.busy, p.busy_since = None, None
            db.commit()
    finally:
        db.close()


@router.post("/plans/{plan_id}/fixes/{fix_id}/apply")
def apply_fix(plan_id: str, fix_id: str, ctx: WorkspaceCtx, db: DB) -> dict:
    plan, proposal = _plan_and_fix(ctx, db, plan_id, fix_id)
    try:
        fixing.apply(db, plan, proposal, _client(ctx, _instance(ctx, plan)))
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return _full(db, plan)


@router.post("/plans/{plan_id}/fixes/{fix_id}/reject")
def reject_fix(plan_id: str, fix_id: str, ctx: WorkspaceCtx, db: DB) -> dict:
    plan, proposal = _plan_and_fix(ctx, db, plan_id, fix_id)
    try:
        fixing.reject(db, plan, proposal)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return _full(db, plan)


def _plan_and_fix(ctx: Ctx, db, plan_id: str, fix_id: str) -> tuple[Plan, FixProposal]:
    plan = _get_plan(ctx, db, plan_id, "build")
    proposal = db.get(FixProposal, fix_id)
    if proposal is None or proposal.plan_id != plan.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That fix isn't on this plan.")
    return plan, proposal


# ---------- Chunk 3: editing a row by hand ----------

class EditIn(BaseModel):
    script: str | None = Field(default=None, max_length=200_000)
    record: dict | None = None


@router.patch("/plans/{plan_id}/components/{component_id}")
def edit_component(plan_id: str, component_id: str, body: EditIn, ctx: WorkspaceCtx, db: DB) -> dict:
    plan = _get_plan(ctx, db, plan_id, "build")
    _busy_guard(plan, db)
    if body.script is None and body.record is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Send the script or the record fields to change.")
    try:
        fixing.edit(db, plan, component_id, body.script, body.record, _client(ctx, _instance(ctx, plan)))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return _full(db, plan)


# ---------- Chunk 4: approve ----------

class ApproveIn(BaseModel):
    ids: list[str] = Field(min_length=1)


@router.post("/plans/{plan_id}/approve")
def approve(plan_id: str, body: ApproveIn, ctx: WorkspaceCtx, db: DB) -> dict:
    plan = _get_plan(ctx, db, plan_id, "approve")
    _busy_guard(plan, db)
    try:
        deploy_svc.approve(db, plan, body.ids, ctx.user.id)
    except DeployError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return _full(db, plan)


@router.post("/plans/{plan_id}/unapprove")
def unapprove(plan_id: str, ctx: WorkspaceCtx, db: DB) -> dict:
    plan = _get_plan(ctx, db, plan_id, "approve")
    _busy_guard(plan, db)
    deploy_svc.unapprove(db, plan)
    return _full(db, plan)


# ---------- Chunk 4: deploy and rollback ----------

class DeployIn(BaseModel):
    update_set_name: str = Field(min_length=1, max_length=80)
    confirm_production: bool = False


@router.post("/plans/{plan_id}/deploy")
def deploy_plan(plan_id: str, body: DeployIn, ctx: WorkspaceCtx, db: DB) -> StreamingResponse:
    plan = _get_plan(ctx, db, plan_id)
    _busy_guard(plan, db)
    inst = _instance(ctx, plan)
    if inst is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Connect a ServiceNow instance before deploying, in Settings → ServiceNow instances.")
    ctx.require_deploy(inst)
    if inst.instance_type == "Production" and not body.confirm_production:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"{inst.name} is a production instance. Confirm before deploying to it.")
    return _run_deploy(ctx, db, plan, inst, "deploying", body.update_set_name)


@router.post("/plans/{plan_id}/rollback")
def rollback_plan(plan_id: str, ctx: WorkspaceCtx, db: DB) -> StreamingResponse:
    plan = _get_plan(ctx, db, plan_id)
    _busy_guard(plan, db)
    deployed_to = (plan.deployment or {}).get("instance_id")
    inst = ctx.instance(deployed_to) if deployed_to else _instance(ctx, plan)
    if inst is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "The instance this was deployed to isn't connected any more, so nowBuilder can't roll it back.")
    ctx.require_deploy(inst)
    return _run_deploy(ctx, db, plan, inst, "rolling back", None)


def _run_deploy(ctx: Ctx, db, plan: Plan, inst: Instance, what: str, update_set_name: str | None) -> StreamingResponse:
    plan.busy, plan.busy_since = ("deploying" if update_set_name else "rolling_back"), datetime.now(UTC)
    db.commit()
    plan_id, instance_id, user_id = plan.id, inst.id, ctx.user.id

    def stream() -> Iterator[str]:
        sdb = SessionLocal()
        try:
            p = sdb.get(Plan, plan_id)
            inst_s = sdb.get(Instance, instance_id)
            client = ServiceNowClient(inst_s, sdb)
            queue: list[dict] = []
            yield _sse({"type": "start", "plan_id": plan_id})
            from ..services.auto_deploy import run_streaming
            try:
                if update_set_name:
                    work = lambda on_status: deploy_svc.deploy(sdb, p, client, inst_s, update_set_name,  # noqa: E731
                                                               user_id, on_status=on_status)
                else:
                    work = lambda on_status: deploy_svc.rollback(sdb, p, client, user_id, on_status=on_status)  # noqa: E731
                for e in run_streaming(work):       # progress reaches the card while it happens
                    yield _sse(e)
                yield _sse({"type": "plan", "plan": plan_out(p)})
                # it finished, but not cleanly: a row that didn't go in, or an update set that
                # captured nothing. The user has to be told, even though nothing was raised.
                done = p.deployment or {}
                if done.get("message"):
                    yield _sse({"type": "error" if done.get("status") == "partial" else "warning",
                                "message": done["message"]})
            except (DeployError, ServiceNowError) as e:
                for ev in queue:
                    yield _sse(ev)
                yield _sse({"type": "plan", "plan": plan_out(p)})
                yield _sse({"type": "error", "message": str(e)})
            finally:
                p.busy, p.busy_since = None, None
                sdb.commit()
            yield _sse({"type": "done"})
        except Exception:  # noqa: BLE001
            _release(plan_id)
            yield _sse({"type": "error", "message": f"nowBuilder hit an unexpected problem while {what}. Try again."})
            raise
        finally:
            sdb.close()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------- Chunk 4: Push to Git ----------

class PushIn(BaseModel):
    repo: str = Field(min_length=3, max_length=140)
    base: str = Field(default="main", max_length=120)
    branch: str | None = Field(default=None, max_length=120)
    ids: list[str] | None = None


@router.post("/plans/{plan_id}/push")
def push_to_git(plan_id: str, body: PushIn, ctx: WorkspaceCtx, db: DB) -> dict:
    from ..services import integrations as integ_svc
    from ..services.github import GitHubError, branch_name

    plan = _get_plan(ctx, db, plan_id, "push")
    integ = integ_svc.get(db, ctx.workspace.id, "github")
    if integ is None:
        who = "Connect it in Settings → GitHub." if ctx.can("manage_integrations") else "Ask a workspace admin to connect it."
        raise HTTPException(status.HTTP_409_CONFLICT, f"GitHub isn't connected yet. {who}")
    files = deploy_svc.files_for(plan, body.ids)
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "There's nothing written in this plan to push yet.")
    chat = db.get(Chat, plan.chat_id)
    jira_key = chat.jira_key if chat else None
    branch = body.branch or branch_name(plan.title, jira_key)
    client = integ_svc.github_client(integ)
    try:
        result = client.push(
            body.repo, body.base, branch, files,
            message=f"{plan.title}\n\nBuilt with nowBuilder.",
            title=f"{jira_key + ': ' if jira_key else ''}{plan.title}",
            body=_pr_body(plan, files),
        )
    except GitHubError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    finally:
        client.close()
    plan.git = {"repo": body.repo, "branch": result.branch, "base": result.base, "commit": result.commit,
                "pr_number": result.pr_number, "pr_url": result.pr_url, "pr_state": result.pr_state,
                "at": _now(), "by": ctx.user.id, "ids": body.ids or [c["id"] for c in plan.components],
                "files": result.files}
    db.commit()
    return _full(db, plan)


def _pr_body(plan: Plan, files: dict[str, str]) -> str:
    rows = "\n".join(f'- **{c["name"]}** ({c["type"].replace("_", " ")})' for c in plan.components if c.get("generated"))
    v = plan.validation or {}
    checks_line = (f'nowBuilder checks: {v.get("errors", 0)} errors, {v.get("warnings", 0)} warnings.'
                   if v else "")
    return f"{plan.summary}\n\n### Artifacts\n{rows}\n\n{checks_line}\n\n{len(files)} files. Built with nowBuilder."
