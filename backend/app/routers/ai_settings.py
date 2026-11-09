"""Settings → AI provider (any provider, key and model) and the AI usage view."""
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..ai import usage
from ..ai.providers import options as provider_options
from ..ai.providers import resolve
from ..config import get_settings
from ..deps import DB, WorkspaceCtx
from ..models import AIProviderConfig
from ..schemas import AIProviderIn, AIProviderOut
from ..security import decrypt, encrypt
from ..services import ai_provider

router = APIRouter(prefix="/api/settings/ai-provider", tags=["settings"])
usage_router = APIRouter(prefix="/api/settings/ai-usage", tags=["settings"])


def _out(cfg: AIProviderConfig) -> AIProviderOut:
    r = resolve(cfg.provider, cfg.base_url)
    return AIProviderOut(
        provider=cfg.provider, provider_name=usage.provider_name(cfg), kind=r.kind,
        base_url=(cfg.base_url or None) if r.key != "custom" else (r.base_url or None), model=cfg.model,
        api_key_masked=f"••••••••{cfg.api_key_last4}", verified=cfg.verified, verified_at=cfg.verified_at,
        status_message=cfg.status_message, updated_at=cfg.updated_at,
    )


@router.get("/options")
def options() -> dict:
    return {"providers": provider_options(), "default_model": get_settings().default_ai_model}


@router.get("", response_model=AIProviderOut | None)
def get_config(ctx: WorkspaceCtx) -> AIProviderOut | None:
    """The workspace's AI provider, shared by every member."""
    cfg = ctx.ai_config()
    return _out(cfg) if cfg else None


@router.put("", response_model=AIProviderOut)
def save_and_verify(body: AIProviderIn, ctx: WorkspaceCtx, db: DB) -> AIProviderOut:
    ctx.require("manage_ai")
    user = ctx.user
    cfg = ctx.ai_config()
    api_key = body.api_key.strip() if body.api_key else (decrypt(cfg.api_key_enc) if cfg else None)
    if not api_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Enter an API key.")
    provider = body.provider.strip()
    preset = resolve(provider, body.base_url)
    provider = preset.key if preset.key != "custom" else provider  # "Claude" → "anthropic"; others kept as typed
    base_url = (body.base_url or "").strip().rstrip("/") or None
    if base_url and not base_url.startswith(("https://", "http://")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The base URL must start with https:// (or http:// for a server on your own network).")
    if preset.kind == "openai" and not (base_url or preset.base_url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{preset.label} needs a base URL: the address of its OpenAI-compatible API, for example https://api.example.com/v1.")
    result = ai_provider.verify(provider, api_key, body.model.strip(), base_url)
    if cfg is None:
        # one row per user (the saver); reuse it if they had one in an earlier workspace
        cfg = db.scalar(select(AIProviderConfig).where(AIProviderConfig.user_id == user.id)) or AIProviderConfig(user_id=user.id)
        cfg.workspace_id = ctx.workspace.id
        db.add(cfg)
    cfg.provider, cfg.provider_name, cfg.model, cfg.base_url = provider, body.provider.strip(), body.model.strip(), base_url
    cfg.api_key_enc, cfg.api_key_last4 = encrypt(api_key), api_key[-4:]
    cfg.verified, cfg.status_message = result.ok, result.message
    cfg.verified_at = datetime.now(UTC) if result.ok else None
    if result.ok:
        cfg.model_info, cfg.rate_limits = result.model_info or {}, result.limits or {}
    cfg.updated_at = datetime.now(UTC)
    db.commit()
    return _out(cfg)


@usage_router.get("")
def get_usage(ctx: WorkspaceCtx, db: DB, month: str | None = None) -> dict:
    """Credits used in a month: by operation, member and day."""
    ctx.require("manage_ai")
    cfg = ctx.ai_config()
    out = usage.summary(db, ctx.workspace.id, cfg.model if cfg else None, month)
    out["provider"] = usage.provider_name(cfg) if cfg else None
    return out
