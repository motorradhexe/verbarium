"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter(tags=["health"])


class DatabaseHealth(BaseModel):
    backend: str
    connected: bool


class HealthResponse(BaseModel):
    status: str
    name: str
    version: str
    environment: str
    database: DatabaseHealth


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health() -> HealthResponse:
    settings = get_settings()

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        connected = True
    except Exception:  # noqa: BLE001 — health must never raise
        connected = False

    return HealthResponse(
        status="ok",
        name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        database=DatabaseHealth(backend=settings.db_backend, connected=connected),
    )
