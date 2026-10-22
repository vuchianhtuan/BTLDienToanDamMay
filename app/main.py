"""Application composition only. Features live in routes/services/storage."""
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.database import create_database
from app.models import Base
from app.routes import files, health
from app.services.files import FileService
from app.storage import create_storage


def create_app(database_url=None, storage=None, max_bytes=None, api_key=None):
    settings = Settings.from_env()
    engine, sessions = create_database(database_url or settings.database_url)
    if storage is None:
        storage = create_storage(settings)
    limit = max_bytes if max_bytes is not None else settings.max_file_bytes
    key = settings.api_key if api_key is None else api_key

    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(Base.metadata.create_all, engine)
        yield
        engine.dispose()

    app = FastAPI(title="File Integrity Lab", version="1.0.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.storage = storage
    app.state.storage_backend = settings.storage_backend
    app.state.max_file_bytes = limit
    app.state.files = FileService(sessions, storage)

    @app.middleware("http")
    async def access_control(request, call_next):
        if request.url.path.startswith("/api/") and key:
            supplied = request.headers.get("X-API-Key", "")
            if not secrets.compare_digest(supplied.encode(), key.encode()):
                return JSONResponse({"detail": "API key required"}, status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    frontend = Path(__file__).resolve().parent.parent / "frontend"
    app.mount("/assets", StaticFiles(directory=frontend), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(frontend / "index.html")

    app.include_router(health.router)
    app.include_router(files.router)
    return app


app = create_app()
