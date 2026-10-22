import logging

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])
log = logging.getLogger("integrity")


@router.get("/live")
def live():
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request):
    state = request.app.state
    try:
        with state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        state.storage.check()
    except Exception:
        log.exception("Readiness check failed")
        raise HTTPException(503, "Database or storage unavailable")
    return {"status": "ready", "storage": state.storage_backend, "max_file_bytes": state.max_file_bytes}
