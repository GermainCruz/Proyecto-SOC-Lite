"""Punto de entrada de la API SOC-Lite."""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import alerts, audit, auth, dashboard, incidents, reports, users
from app.core.config import get_settings
from app.db.session import engine
from app.schemas import HealthOut
from app.services import audit as audit_service

settings = get_settings()
logger = structlog.get_logger("soc-lite")

API_VERSION = "1.0.0"
AUDITED_PREFIXES = ("alerts", "triage", "incidents", "reports", "users", "roles", "audit", "dashboard", "auth")
SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/api/v1/health"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.reports_dir).mkdir(parents=True, exist_ok=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_ready", url=settings.database_url.split("@")[-1])
    except Exception:
        logger.exception("database_unavailable")
    yield
    await engine.dispose()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Propaga request-id, mide latencia y alimenta la bitácora de acceso."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.UUID(request.headers.get("x-request-id", str(uuid.uuid4())))
        request.state.request_id = request_id
        started = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - t0) * 1000
        response.headers["X-Request-ID"] = str(request_id)
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.1f}"

        path = request.url.path
        if path.startswith(settings.api_prefix + "/") and path not in SKIP_PATHS:
            parts = path[len(settings.api_prefix) + 1 :].split("/")
            module = parts[0] if parts and parts[0] else "root"
            if module in AUDITED_PREFIXES and module != "auth":
                user = getattr(request.state, "current_user", None)
                await audit_service.record_access(
                    user=user,
                    module=module,
                    method=request.method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_id=request_id,
                    ip_address=(request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                                or (request.client.host if request.client else None)),
                    user_agent=request.headers.get("user-agent"),
                    started_at=started,
                )
        return response


app = FastAPI(
    title=settings.app_name,
    version=API_VERSION,
    description=(
        "API de triaje automático de alertas SOC para PYME, mediana empresa y organismo público. "
        "Incluye RBAC, bitácora de auditoría inmutable y reportes PDF/Word/Excel."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
    contact={"name": "Equipo SOC-Lite"},
    license_info={"name": "Uso académico"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time-ms"],
)
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Datos de entrada inválidos",
            "errors": exc.errors(),
            "request_id": str(getattr(request.state, "request_id", "")),
        },
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Error interno del servidor",
            "request_id": str(getattr(request.state, "request_id", "")),
        },
    )


# --------------------------------------------------------------------- Rutas
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(users.roles_router, prefix=settings.api_prefix)
app.include_router(alerts.router, prefix=settings.api_prefix)
app.include_router(incidents.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)


@app.get("/health", response_model=HealthOut, tags=["Operación"], summary="Estado del servicio")
@app.get(f"{settings.api_prefix}/health", response_model=HealthOut, include_in_schema=False)
async def health() -> HealthOut:
    database_ok = True
    ai_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        database_ok = False

    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(f"{settings.ai_service_url.rstrip('/')}/health")
            ai_ok = response.status_code == 200
    except httpx.HTTPError:
        ai_ok = False

    return HealthOut(
        status="ok" if database_ok else "degraded",
        version=API_VERSION,
        database=database_ok,
        ai_service=ai_ok,
        checked_at=datetime.now(timezone.utc),
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, Any]:
    return {
        "service": settings.app_name,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
