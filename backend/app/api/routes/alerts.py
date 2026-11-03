"""Gestión de alertas: consulta, filtros, triaje asistido y escalamiento."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, client_context, require
from app.db.models import Alert, AlertSource, Incident, IncidentAlert, TriageResult, User
from app.db.session import get_session
from app.schemas import (
    AlertCreate,
    AlertDetail,
    AlertOut,
    AlertPage,
    AlertUpdate,
    Severity,
    TriageOut,
    TriageReview,
)
from app.services import ai_client, audit

router = APIRouter(prefix="/alerts", tags=["Alertas"])
ALERT_LOAD = (
    selectinload(Alert.triage_results),
    selectinload(Alert.enrichments),
)


async def _load_alert(session: AsyncSession, alert_id: uuid.UUID) -> Alert:
    """Recarga la alerta con sus relaciones para serializar sin lazy-load async."""
    alert = (
        await session.execute(select(Alert).where(Alert.id == alert_id).options(*ALERT_LOAD))
    ).scalars().unique().one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta inexistente")
    return alert


def _apply_filters(stmt, severity, alert_status, source, q, date_from, date_to, agent):
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if alert_status:
        stmt = stmt.where(Alert.status == alert_status)
    if source:
        stmt = stmt.where(Alert.source.has(AlertSource.code == source))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Alert.title.ilike(like), Alert.agent_name.ilike(like), Alert.rule_id.ilike(like)))
    if agent:
        stmt = stmt.where(Alert.agent_name == agent)
    if date_from:
        stmt = stmt.where(Alert.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
    if date_to:
        stmt = stmt.where(
            Alert.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        )
    return stmt


@router.get("", response_model=AlertPage, summary="Listar alertas con filtros y paginación")
async def list_alerts(
    _: CurrentUser = Depends(require("alerts:read")),
    session: AsyncSession = Depends(get_session),
    severity: Severity | None = None,
    status_: str | None = Query(default=None, alias="status"),
    source: str | None = Query(default=None, max_length=32),
    q: str | None = Query(default=None, max_length=120),
    agent: str | None = Query(default=None, max_length=120),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default="-created_at", pattern="^-?(created_at|severity|rule_level|last_seen_at)$"),
) -> AlertPage:
    filters = (severity, status_, source, q, date_from, date_to, agent)
    base = _apply_filters(select(Alert), *filters)

    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    pages = max((total + page_size - 1) // page_size, 1)

    order_map = {
        "created_at": Alert.created_at.asc(), "-created_at": Alert.created_at.desc(),
        "severity": Alert.severity.asc(), "-severity": Alert.severity.desc(),
        "rule_level": Alert.rule_level.asc(), "-rule_level": Alert.rule_level.desc(),
        "last_seen_at": Alert.last_seen_at.asc(), "-last_seen_at": Alert.last_seen_at.desc(),
    }
    stmt = (
        base.order_by(order_map[sort])
        .limit(page_size)
        .offset((page - 1) * page_size)
        .options(*ALERT_LOAD)
    )
    items = list((await session.execute(stmt)).scalars().unique().all())
    return AlertPage(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{alert_id}", response_model=AlertDetail, summary="Detalle de alerta con evidencias")
async def get_alert(
    alert_id: uuid.UUID,
    _: CurrentUser = Depends(require("alerts:read")),
    session: AsyncSession = Depends(get_session),
) -> AlertDetail:
    alert = (
        await session.execute(select(Alert).where(Alert.id == alert_id).options(*ALERT_LOAD))
    ).scalars().unique().one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta inexistente")

    incident_code = (
        await session.execute(
            select(Incident.code)
            .join(IncidentAlert, IncidentAlert.incident_id == Incident.id)
            .where(IncidentAlert.alert_id == alert_id)
            .limit(1)
        )
    ).scalar_one_or_none()

    detail = AlertDetail.model_validate(alert)
    detail.incident_code = incident_code
    return detail


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED, summary="Registrar alerta manual")
async def create_alert(
    payload: AlertCreate,
    request: Request,
    user: CurrentUser = Depends(require("alerts:create")),
    session: AsyncSession = Depends(get_session),
) -> Alert:
    source = (
        await session.execute(select(AlertSource).where(AlertSource.code == "manual"))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=500, detail="Fuente 'manual' no configurada")

    alert = Alert(
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        rule_id=payload.rule_id,
        src_ip=payload.src_ip,
        dst_ip=payload.dst_ip,
        agent_name=payload.agent_name,
        raw_payload=payload.raw_payload,
        source_id=source.id,
        status="pending",
    )
    session.add(alert)
    await session.flush()
    await audit.record(
        action="alerts.create", module="alerts", user=user, entity="alert", entity_id=alert.id,
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={"title": payload.title, "severity": payload.severity}, session=session,
    )
    await session.commit()
    return await _load_alert(session, alert.id)


@router.patch("/{alert_id}", response_model=AlertOut, summary="Actualizar estado, severidad o asignación")
async def update_alert(
    alert_id: uuid.UUID,
    payload: AlertUpdate,
    request: Request,
    user: CurrentUser = Depends(require("alerts:update")),
    session: AsyncSession = Depends(get_session),
) -> Alert:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta inexistente")

    before = {"status": str(alert.status), "severity": str(alert.severity), "assigned_to": str(alert.assigned_to or "")}
    changes: dict[str, Any] = {}

    if payload.status is not None:
        alert.status = payload.status
        changes["status"] = payload.status
    if payload.severity is not None:
        alert.severity = payload.severity
        changes["severity"] = payload.severity
    if payload.assigned_to is not None:
        assignee = await session.get(User, payload.assigned_to)
        if assignee is None or not assignee.is_active:
            raise HTTPException(status_code=422, detail="Asignado inexistente o inactivo")
        alert.assigned_to = payload.assigned_to
        alert.assigned_at = datetime.now(timezone.utc)
        changes["assigned_to"] = str(payload.assigned_to)

    await audit.record(
        action="alerts.update", module="alerts", user=user, entity="alert", entity_id=alert.id,
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={"before": before, "changes": changes, "comment": payload.comment}, session=session,
    )
    await session.commit()
    return await _load_alert(session, alert.id)


@router.post("/{alert_id}/triage", response_model=TriageOut, summary="Ejecutar triaje con IA")
async def run_triage(
    alert_id: uuid.UUID,
    request: Request,
    force: bool = Query(default=False, description="Re-ejecuta aunque exista un triaje previo"),
    user: CurrentUser = Depends(require("triage:run")),
    session: AsyncSession = Depends(get_session),
) -> TriageResult:
    alert = (
        await session.execute(select(Alert).where(Alert.id == alert_id).options(selectinload(Alert.asset)))
    ).scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta inexistente")

    if not force:
        existing = (
            await session.execute(
                select(TriageResult)
                .where(TriageResult.alert_id == alert_id)
                .order_by(TriageResult.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    asset_criticality = alert.asset.criticality if alert.asset else "medium"
    alert_payload = {
        "alert_id": str(alert.id),
        "alert": {
            "title": alert.title,
            "description": alert.description,
            "severity": str(alert.severity),
            "rule_id": alert.rule_id,
            "rule_level": alert.rule_level,
            "src_ip": str(alert.src_ip) if alert.src_ip else None,
            "dst_ip": str(alert.dst_ip) if alert.dst_ip else None,
            "agent_name": alert.agent_name,
            "mitre_tactic": alert.mitre_tactic,
            "mitre_technique": alert.mitre_technique,
            "raw_payload": alert.raw_payload,
        },
        "context": {
            "asset_criticality": asset_criticality,
            "historical_false_positive_rate": 0.18,
        },
    }

    try:
        result = await ai_client.request_triage(alert_payload)
    except ai_client.TriageUnavailable:
        result = ai_client.heuristic_triage(alert_payload["alert"], asset_criticality)

    triage = TriageResult(
        alert_id=alert.id,
        engine=result.get("engine", "langchain"),
        model=result.get("model", "desconocido"),
        prompt_version=result.get("prompt_version", "v1.2"),
        suggested_severity=result["suggested_severity"],
        verdict=result["verdict"],
        confidence=result.get("confidence"),
        summary=result["summary"],
        recommended_actions=result.get("recommended_actions", []),
        mitre_techniques=result.get("mitre_techniques", []),
        evidence=result.get("evidence", {}),
        tokens_in=result.get("tokens_in"),
        tokens_out=result.get("tokens_out"),
        latency_ms=result.get("latency_ms"),
        cost_usd=result.get("cost_usd"),
        needs_human_review=result.get("needs_human_review", False),
    )
    session.add(triage)

    alert.severity = result["suggested_severity"]
    if result["verdict"] == "true_positive":
        alert.status = "triaged"
    elif result["verdict"] in ("benign", "false_positive"):
        alert.status = "false_positive" if result["verdict"] == "false_positive" else "in_review"
    else:
        alert.status = "in_review"

    await audit.record(
        action="triage.run", module="triage", user=user, entity="alert", entity_id=alert.id,
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={
            "model": triage.model, "verdict": result["verdict"],
            "confidence": result.get("confidence"), "force": force,
            "fallback": triage.engine == "heuristic",
        },
        session=session,
    )
    await session.commit()
    await session.refresh(triage)
    return triage


@router.post("/{alert_id}/review", response_model=TriageOut, summary="Validar el triaje (revisión humana)")
async def review_triage(
    alert_id: uuid.UUID,
    payload: TriageReview,
    request: Request,
    user: CurrentUser = Depends(require("triage:review")),
    session: AsyncSession = Depends(get_session),
) -> TriageResult:
    triage = (
        await session.execute(
            select(TriageResult)
            .where(TriageResult.alert_id == alert_id)
            .order_by(TriageResult.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if triage is None:
        raise HTTPException(status_code=404, detail="La alerta no tiene triaje previo")

    previous = str(triage.human_verdict or triage.verdict)
    triage.human_verdict = payload.verdict
    triage.reviewed_by = user.id
    triage.reviewed_at = datetime.now(timezone.utc)
    triage.needs_human_review = False

    alert = await session.get(Alert, alert_id)
    if alert is not None:
        if payload.verdict == "false_positive":
            alert.status = "false_positive"
        elif payload.verdict == "true_positive":
            alert.status = "triaged"
        elif payload.verdict == "benign":
            alert.status = "closed"
        else:
            alert.status = "in_review"

    await audit.record(
        action="triage.review", module="triage", user=user, entity="triage_result", entity_id=triage.id,
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={"alert_id": str(alert_id), "previous": previous, "human_verdict": payload.verdict,
                "comment": payload.comment},
        session=session,
    )
    await session.commit()
    await session.refresh(triage)
    return triage


@router.post("/{alert_id}/escalate", status_code=status.HTTP_201_CREATED, summary="Escalar a incidente")
async def escalate_alert(
    alert_id: uuid.UUID,
    request: Request,
    user: CurrentUser = Depends(require("incidents:create")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta inexistente")

    incident_id = (
        await session.execute(
            text("SELECT soc.fn_open_incident(:alert_id, :user_id)"),
            {"alert_id": str(alert_id), "user_id": str(user.id)},
        )
    ).scalar_one()
    incident_code = (await session.get(Incident, incident_id)).code

    await audit.record(
        action="incidents.create", module="incidents", user=user, entity="incident",
        entity_id=str(incident_id), ip_address=client_context(request)["ip"],
        user_agent=request.headers.get("user-agent"),
        detail={"from_alert": str(alert_id), "code": incident_code}, session=session,
    )
    await session.commit()
    return {"incident_id": str(incident_id), "code": incident_code}


@router.get("/{alert_id}/timeline", summary="Línea de tiempo de la alerta")
async def alert_timeline(
    alert_id: uuid.UUID,
    _: CurrentUser = Depends(require("alerts:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta inexistente")

    events: list[dict[str, Any]] = [
        {"at": alert.created_at, "kind": "alert.created", "detail": "Alerta recibida del SIEM"},
    ]
    triages = (
        await session.execute(
            select(TriageResult).where(TriageResult.alert_id == alert_id).order_by(TriageResult.created_at)
        )
    ).scalars().all()
    for row in triages:
        events.append({"at": row.created_at, "kind": "triage.completed", "detail": row.summary[:180]})
    return sorted(events, key=lambda e: e["at"])


