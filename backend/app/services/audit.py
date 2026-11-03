"""Bitácora de auditoría: escritura append-only con contexto de usuario y request.

La integridad (encadenamiento SHA-256 e inmutabilidad) la garantiza PostgreSQL
mediante los triggers `trg_audit_hash` y `trg_audit_no_update`. Esta capa solo
aporta el contexto de negocio: quién, desde dónde, sobre qué y con qué resultado.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.models import AuditLog
from app.db.session import SessionLocal
from app.schemas import AuditResult

logger = structlog.get_logger(__name__)


async def record(
    *,
    action: str,
    module: str,
    user: CurrentUser | None = None,
    entity: str | None = None,
    entity_id: str | None = None,
    result: AuditResult = "success",
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
    session: AsyncSession | None = None,
) -> None:
    """Inserta un evento. Si no se pasa sesión, abre una propia y hace commit."""
    entry = AuditLog(
        occurred_at=occurred_at or datetime.now(timezone.utc),
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        role_code=user.role_code if user else None,
        action=action,
        module=module,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        result=result,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:500] or None,
        request_id=request_id,
        detail=detail or {},
    )
    if session is not None:
        session.add(entry)
        return

    try:
        async with SessionLocal() as own_session:
            own_session.add(entry)
            await own_session.commit()
    except Exception:  # la auditoría nunca debe tumbar la operación de negocio
        logger.exception("audit_write_failed", action=action, module=module)


async def record_access(
    *,
    user: CurrentUser | None,
    module: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: uuid.UUID,
    ip_address: str | None,
    user_agent: str | None,
    started_at: datetime,
) -> None:
    """Registra la entrada y la salida de un módulo (requisito de trazabilidad)."""
    result: AuditResult = "success" if status_code < 400 else ("denied" if status_code in (401, 403) else "error")
    base_detail = {"method": method, "path": path, "status": status_code}
    try:
        async with SessionLocal() as session:
            await record(
                action=f"{module}.enter",
                module=module,
                user=user,
                entity="request",
                entity_id=str(request_id),
                result="success",
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                detail={**base_detail, "phase": "in"},
                occurred_at=started_at,
                session=session,
            )
            # Flush explícito: el trigger de encadenamiento debe ver la fila
            # anterior ya insertada (un INSERT multi-fila rompería la cadena).
            await session.flush()
            await record(
                action=f"{module}.exit",
                module=module,
                user=user,
                entity="request",
                entity_id=str(request_id),
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                detail={**base_detail, "phase": "out", "duration_ms": round(duration_ms, 2)},
                occurred_at=datetime.now(timezone.utc),
                session=session,
            )
            await session.commit()
    except Exception:
        logger.exception("audit_access_failed", module=module, path=path)
