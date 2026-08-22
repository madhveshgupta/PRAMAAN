"""FastAPI application entry point:  uvicorn api.app.main:app --reload --port 8000"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.app.config import get_settings
from api.app.db import SessionLocal
from api.app.services import storage

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
                    datefmt="%H:%M:%S")

app = FastAPI(title="PRAMAAN API", version="0.1.0",
              description="DPR quality assessment and risk prediction. "
                          "Advisory only — the system never approves or rejects.")

app.add_middleware(CORSMiddleware, allow_origins=get_settings().allowed_origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

API_V1 = "/api/v1"


@app.get(f"{API_V1}/health")
def health() -> dict:
    """Liveness for the whole stack. The worker check is 'has one polled recently',
    since the worker is a separate process and easy to forget to start."""
    out: dict[str, object] = {"status": "ok"}

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        out["db"] = "ok"
        row = db.execute(text(
            "SELECT count(*) FROM jobs WHERE status = 'running' "
            "AND locked_at > now() - interval '2 minutes'")).scalar()
        out["worker"] = "ok" if row is not None else "unknown"
        out["queue_depth"] = db.execute(text(
            "SELECT count(*) FROM jobs WHERE status = 'queued'")).scalar()
    except Exception as exc:                       # noqa: BLE001
        out["db"] = f"error: {type(exc).__name__}"
        out["status"] = "degraded"
    finally:
        db.close()

    out["storage"] = "ok" if storage.health() else "error"
    if out["storage"] != "ok":
        out["status"] = "degraded"

    s = get_settings()
    out["demo_mode"] = s.demo_mode
    return out


def _register_routers() -> None:
    """Routers are added as their phases land; a missing one must not stop the app."""
    log = logging.getLogger("pramaan.api")
    from api.app.routes import auth
    app.include_router(auth.router, prefix=API_V1)
    for name in ("dprs", "findings", "assessments", "governance"):
        try:
            module = __import__(f"api.app.routes.{name}", fromlist=["router"])
            app.include_router(module.router, prefix=API_V1)
        except ImportError as exc:
            log.debug("router %s not available yet: %s", name, exc)


_register_routers()
