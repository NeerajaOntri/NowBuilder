import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import ai_settings, auth, chats, instances, integrations, plans, platform, workspace
from .services.workspace import AccessError, LimitError
from .security import BadEncryptionKey, SecretUnreadable


@asynccontextmanager
async def lifespan(_: FastAPI):
    from .db import DatabaseUnreachable
    try:
        init_db()
    except DatabaseUnreachable as e:
        logging.getLogger("nowbuilder").error("%s", e)
        raise SystemExit(3) from None
    yield


app = FastAPI(title="nowBuilder API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(instances.router)
app.include_router(ai_settings.router)
app.include_router(ai_settings.usage_router)
app.include_router(chats.router)
app.include_router(plans.router)
app.include_router(workspace.router)
app.include_router(integrations.router)
app.include_router(platform.router)


def _serve_frontend() -> None:
    """When the built frontend is next to the backend (Docker image for hosting), serve it from here:
    one address for the app and /api, no CORS, and links like /invite/<token> open the app."""
    from pathlib import Path

    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    root = Path(get_settings().static_dir).resolve()
    index = root / "index.html"
    if not index.is_file():
        return

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/") or path == "api":
            raise HTTPException(404, "Not found")
        file = (root / path).resolve()
        if path and file.is_file() and root in file.parents:
            return FileResponse(file)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


@app.exception_handler(SecretUnreadable)
@app.exception_handler(BadEncryptionKey)
async def secret_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(AccessError)
async def access_error(_: Request, exc: Exception) -> JSONResponse:
    code = getattr(exc, "code", None)
    return JSONResponse(status_code=403, content={"detail": str(exc), **({"code": code} if code else {})})


@app.exception_handler(LimitError)
async def limit_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


_serve_frontend()  # last, so every /api route above wins
