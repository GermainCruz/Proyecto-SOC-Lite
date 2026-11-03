"""Reportes operacionales y de gestión en PDF, Word y Excel."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, client_context, require
from app.db.models import Report
from app.db.session import get_session
from app.schemas import ReportOut, ReportRequest
from app.services import audit, reports as report_service

router = APIRouter(prefix="/reports", tags=["Reportes"])

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


async def _next_code(session: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    total = (
        await session.execute(
            select(func.count()).select_from(Report).where(func.date_part("year", Report.created_at) == year)
        )
    ).scalar_one()
    return f"RPT-{year}-{total + 1:04d}"


@router.get("", response_model=list[ReportOut], summary="Listar reportes")
async def list_reports(
    _: CurrentUser = Depends(require("reports:read")),
    session: AsyncSession = Depends(get_session),
    kind: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Report]:
    stmt = select(Report).order_by(Report.created_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(Report.kind == kind)
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED, summary="Generar reporte")
async def generate_report(
    payload: ReportRequest,
    request: Request,
    user: CurrentUser = Depends(require("reports:generate")),
    session: AsyncSession = Depends(get_session),
) -> Report:
    report = Report(
        code=await _next_code(session),
        title=payload.title,
        kind=payload.kind,
        format=payload.format,
        period_start=payload.period_start,
        period_end=payload.period_end,
        filters=payload.filters,
        generated_by=user.id,
        status="pending",
    )
    session.add(report)
    await session.flush()

    try:
        data = await report_service.collect(session, payload.period_start, payload.period_end)
        path = await run_in_threadpool(
            report_service.build, data, str(report.id), payload.title, payload.kind, payload.format
        )
        report.file_path = str(path)
        report.file_size = Path(path).stat().st_size
        report.checksum = await run_in_threadpool(report_service.checksum, Path(path))
        report.status = "completed"
        report.completed_at = datetime.now(timezone.utc)
    except Exception as exc:  # se registra el fallo y se informa al cliente
        report.status = "failed"
        await audit.record(
            action="reports.generate", module="reports", user=user, result="error",
            entity="report", entity_id=report.id, ip_address=client_context(request)["ip"],
            user_agent=request.headers.get("user-agent"),
            detail={"format": payload.format, "error": str(exc)[:300]}, session=session,
        )
        await session.commit()
        raise HTTPException(status_code=500, detail="No fue posible generar el reporte") from exc

    await audit.record(
        action="reports.generate", module="reports", user=user, entity="report", entity_id=report.id,
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={
            "format": payload.format, "kind": payload.kind,
            "period": [str(payload.period_start), str(payload.period_end)],
            "checksum": report.checksum,
        },
        session=session,
    )
    await session.commit()
    await session.refresh(report)
    return report


@router.get("/{report_id}/download", summary="Descargar reporte")
async def download_report(
    report_id: uuid.UUID,
    request: Request,
    user: CurrentUser = Depends(require("reports:download")),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    report = await session.get(Report, report_id)
    if report is None or report.status != "completed" or not report.file_path:
        raise HTTPException(status_code=404, detail="Reporte no disponible")

    path = Path(report.file_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="El archivo del reporte ya no existe")

    await audit.record(
        action="reports.download", module="reports", user=user, entity="report",
        entity_id=report.id, ip_address=client_context(request)["ip"],
        user_agent=request.headers.get("user-agent"),
        detail={"format": str(report.format), "code": report.code}, session=session,
    )
    await session.commit()

    filename = f"{report.code}_{report.kind}.{report.format}"
    return FileResponse(
        path=str(path),
        media_type=MEDIA_TYPES.get(str(report.format), "application/octet-stream"),
        filename=filename,
    )


@router.get("/{report_id}", response_model=ReportOut, summary="Detalle de reporte")
async def get_report(
    report_id: uuid.UUID,
    _: CurrentUser = Depends(require("reports:read")),
    session: AsyncSession = Depends(get_session),
) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Reporte inexistente")
    return report
