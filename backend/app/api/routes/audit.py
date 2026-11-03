"""Consulta y verificación de la bitácora de auditoría (solo lectura)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require
from app.db.models import AuditLog
from app.db.session import get_session
from app.schemas import AuditPage, ChainVerification

router = APIRouter(prefix="/audit", tags=["Auditoría"])


@router.get("", response_model=AuditPage, summary="Consultar la bitácora")
async def list_audit(
    _: CurrentUser = Depends(require("audit:read")),
    session: AsyncSession = Depends(get_session),
    user_email: str | None = None,
    module: str | None = None,
    action: str | None = None,
    result: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> AuditPage:
    stmt = select(AuditLog)
    if user_email:
        stmt = stmt.where(AuditLog.user_email == user_email)
    if module:
        stmt = stmt.where(AuditLog.module == module)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if result:
        stmt = stmt.where(AuditLog.result == result)
    if date_from:
        stmt = stmt.where(AuditLog.occurred_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        stmt = stmt.where(
            AuditLog.occurred_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )

    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return AuditPage(items=list(rows), total=total, page=page, page_size=page_size)


@router.get("/verify", response_model=ChainVerification, summary="Verificar integridad de la cadena")
async def verify_chain(
    actor: CurrentUser = Depends(require("audit:read")),
    session: AsyncSession = Depends(get_session),
    date_from: date | None = None,
    date_to: date | None = None,
) -> ChainVerification:
    start = datetime.combine(date_from or date(2026, 1, 1), time.min, tzinfo=timezone.utc)
    end = datetime.combine(date_to or date.today(), time.max, tzinfo=timezone.utc)
    row = (
        await session.execute(
            text("SELECT total, broken FROM soc.fn_verify_audit_chain(:start, :end)"),
            {"start": start, "end": end},
        )
    ).one()
    return ChainVerification(
        total=row.total,
        broken=row.broken,
        intact=row.broken == 0,
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/summary", summary="Actividad por módulo y usuario")
async def audit_summary(
    _: CurrentUser = Depends(require("audit:read")),
    session: AsyncSession = Depends(get_session),
    days: int = Query(default=7, ge=1, le=90),
) -> dict[str, list[dict[str, object]]]:
    by_module = await session.execute(
        text(
            """
            SELECT module, count(*) AS total,
                   count(*) FILTER (WHERE result <> 'success') AS failures
              FROM soc.audit_log
             WHERE occurred_at > now() - make_interval(days => :days)
             GROUP BY module ORDER BY total DESC
            """
        ),
        {"days": days},
    )
    by_user = await session.execute(
        text(
            """
            SELECT coalesce(user_email::text, 'sistema') AS user_email, count(*) AS total,
                   max(occurred_at) AS last_seen
              FROM soc.audit_log
             WHERE occurred_at > now() - make_interval(days => :days)
             GROUP BY user_email ORDER BY total DESC LIMIT 10
            """
        ),
        {"days": days},
    )
    return {
        "by_module": [dict(r) for r in by_module.mappings()],
        "by_user": [dict(r) for r in by_user.mappings()],
    }


@router.get("/{entry_id}", response_model=AuditPage, summary="Eventos de una entidad")
async def entity_trail(
    entry_id: str,
    _: CurrentUser = Depends(require("audit:read")),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=500),
) -> AuditPage:
    rows = (
        await session.execute(
            select(AuditLog)
            .where(AuditLog.entity_id == entry_id)
            .order_by(AuditLog.occurred_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return AuditPage(items=list(rows), total=len(rows), page=1, page_size=limit)
