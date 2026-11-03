"""Incidentes: apertura con SLA, investigación, cierre y vínculo con alertas."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, client_context, require
from app.db.models import Alert, Incident, IncidentAlert, SlaPolicy, User
from app.db.session import get_session
from app.schemas import IncidentCreate, IncidentOut, IncidentUpdate
from app.services import audit

router = APIRouter(prefix="/incidents", tags=["Incidentes"])


async def _next_code(session: AsyncSession) -> str:
    """Genera INC-AAAA-000NN con bloqueo de asesoría para evitar colisiones."""
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('soc.incidents.code'))"))
    year = datetime.now(timezone.utc).year
    total = (
        await session.execute(
            select(func.count()).select_from(Incident).where(func.date_part("year", Incident.opened_at) == year)
        )
    ).scalar_one()
    return f"INC-{year}-{total + 1:05d}"


@router.get("", response_model=list[IncidentOut], summary="Listar incidentes")
async def list_incidents(
    _: CurrentUser = Depends(require("incidents:read")),
    session: AsyncSession = Depends(get_session),
    state: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    assigned_to: uuid.UUID | None = None,
    overdue: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.opened_at.desc()).limit(limit).offset(offset)
    if state:
        stmt = stmt.where(Incident.status == state)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if assigned_to:
        stmt = stmt.where(Incident.assigned_to == assigned_to)
    if overdue:
        stmt = stmt.where(Incident.status != "closed", Incident.sla_due_at < datetime.now(timezone.utc))
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED, summary="Abrir incidente")
async def create_incident(
    payload: IncidentCreate,
    request: Request,
    user: CurrentUser = Depends(require("incidents:create")),
    session: AsyncSession = Depends(get_session),
) -> Incident:
    policy = await session.get(SlaPolicy, payload.severity)
    if policy is None:
        raise HTTPException(status_code=500, detail="Política SLA no configurada para la severidad")

    asset_id = None
    if payload.alert_id:
        alert = await session.get(Alert, payload.alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alerta inexistente")
        asset_id = alert.asset_id

    incident = Incident(
        code=await _next_code(session),
        title=payload.title,
        severity=payload.severity,
        assigned_to=payload.assigned_to,
        asset_id=asset_id,
        sla_due_at=datetime.now(timezone.utc) + timedelta(minutes=policy.resolve_minutes),
        created_by=user.id,
        status="open",
    )
    session.add(incident)
    await session.flush()

    if payload.alert_id:
        session.add(IncidentAlert(incident_id=incident.id, alert_id=payload.alert_id))
        alert = await session.get(Alert, payload.alert_id)
        if alert is not None:
            alert.status = "escalated"

    await audit.record(
        action="incidents.create", module="incidents", user=user, entity="incident",
        entity_id=incident.id, ip_address=client_context(request)["ip"],
        user_agent=request.headers.get("user-agent"),
        detail={"code": incident.code, "severity": payload.severity, "alert_id": str(payload.alert_id or "")},
        session=session,
    )
    await session.commit()
    await session.refresh(incident)
    return incident


@router.patch("/{incident_id}", response_model=IncidentOut, summary="Actualizar incidente")
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    request: Request,
    user: CurrentUser = Depends(require("incidents:update")),
    session: AsyncSession = Depends(get_session),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incidente inexistente")

    changes: dict[str, object] = {}
    if payload.status is not None:
        incident.status = payload.status
        changes["status"] = payload.status
        if payload.status == "closed":
            if not payload.resolution and not incident.resolution:
                raise HTTPException(status_code=422, detail="El cierre requiere una resolución")
            incident.closed_at = datetime.now(timezone.utc)
    if payload.assigned_to is not None:
        assignee = await session.get(User, payload.assigned_to)
        if assignee is None:
            raise HTTPException(status_code=422, detail="Responsable inexistente")
        incident.assigned_to = payload.assigned_to
        changes["assigned_to"] = str(payload.assigned_to)
    if payload.resolution is not None:
        incident.resolution = payload.resolution
        changes["resolution"] = "actualizada"
    if payload.ticket_ref is not None:
        incident.ticket_ref = payload.ticket_ref
        changes["ticket_ref"] = payload.ticket_ref

    await audit.record(
        action="incidents.update", module="incidents", user=user, entity="incident",
        entity_id=incident.id, ip_address=client_context(request)["ip"],
        user_agent=request.headers.get("user-agent"), detail={"changes": changes}, session=session,
    )
    await session.commit()
    await session.refresh(incident)
    return incident


@router.get("/stats/sla", summary="Cumplimiento de SLA")
async def sla_stats(
    _: CurrentUser = Depends(require("incidents:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, float | int]:
    total = (await session.execute(select(func.count()).select_from(Incident))).scalar_one()
    closed = (
        await session.execute(select(func.count()).select_from(Incident).where(Incident.status == "closed"))
    ).scalar_one()
    breached = (
        await session.execute(
            select(func.count()).select_from(Incident).where(
                Incident.status != "closed", Incident.sla_due_at < datetime.now(timezone.utc)
            )
        )
    ).scalar_one()
    mttr = (
        await session.execute(
            select(func.avg(extract("epoch", Incident.closed_at - Incident.opened_at)) / 60.0).where(
                Incident.closed_at.is_not(None)
            )
        )
    ).scalar_one()
    return {
        "total": total,
        "closed": closed,
        "open": total - closed,
        "breached": breached,
        "compliance_pct": round(100.0 * (1 - breached / total), 2) if total else 100.0,
        "mttr_minutes": round(float(mttr), 2) if mttr is not None else 0.0,
    }


@router.get("/{incident_id}", response_model=IncidentOut, summary="Detalle de incidente")
async def get_incident(
    incident_id: uuid.UUID,
    _: CurrentUser = Depends(require("incidents:read")),
    session: AsyncSession = Depends(get_session),
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incidente inexistente")
    return incident


@router.get("/{incident_id}/alerts", summary="Alertas vinculadas al incidente")
async def incident_alerts(
    incident_id: uuid.UUID,
    _: CurrentUser = Depends(require("incidents:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incidente inexistente")

    rows = await session.execute(
        select(Alert.id, Alert.title, Alert.severity, Alert.status, Alert.created_at)
        .join(IncidentAlert, IncidentAlert.alert_id == Alert.id)
        .where(IncidentAlert.incident_id == incident_id)
        .order_by(Alert.created_at)
    )
    return [
        {"id": str(aid), "title": title, "severity": str(sev), "status": str(st), "created_at": created}
        for aid, title, sev, st, created in rows.all()
    ]


