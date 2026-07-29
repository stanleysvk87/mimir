import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.applog import logger, setup_logging
from app.auth import require_auth
from app.db import init_db
from app.routes_ai import router as ai_router
from app.routes_attachments import router as attachments_router
from app.routes_auth import router as auth_router
from app.routes_checklist import router as checklist_router
from app.routes_entries import router as entries_router
from app.routes_projects import router as projects_router
from app.routes_threads import router as threads_router

app = FastAPI(title="mimir")

# Frontend is a static build served by the same nginx container in
# production; CORS with credentials is only needed for local `npm run dev`
# hitting the backend on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(entries_router)
app.include_router(attachments_router)
app.include_router(projects_router)
app.include_router(checklist_router)
app.include_router(threads_router)
app.include_router(ai_router)


@app.on_event("startup")
def on_startup():
    setup_logging()
    init_db()


@app.exception_handler(Exception)
async def log_unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/settings", dependencies=[Depends(require_auth)])
def get_settings():
    """`sindri_url`, if set, lets the frontend render a real link for
    entries with a `sindri_script_id`. Empty by default -- this is a
    per-instance config value, never a hardcoded default, matching the
    no-personal-defaults rule this app is built to follow."""
    return {"sindri_url": os.environ.get("MIMIR_SINDRI_URL", "").rstrip("/")}
