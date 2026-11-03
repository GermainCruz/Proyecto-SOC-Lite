"""Dashboard: KPIs, series temporales y distribución de alertas."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require
from app.db.session import get_session
from app.schemas import DashboardOut
from app.services import metrics

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardOut, summary="Panel completo del SOC")
async def get_dashboard(
    _: CurrentUser = Depends(require("dashboard:read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await metrics.dashboard(session)


@router.get("/kpis", summary="Solo indicadores (para widgets)")
async def get_kpis(
    _: CurrentUser = Depends(require("dashboard:read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await metrics.kpis(session)


@router.get("/trend", summary="Serie diaria de alertas")
async def get_trend(
    _: CurrentUser = Depends(require("dashboard:read")),
    session: AsyncSession = Depends(get_session),
    days: int = 14,
) -> list[dict]:
    return await metrics.daily_volume(session, max(1, min(days, 90)))


@router.get("/sla", summary="Cumplimiento de SLA")
async def get_sla(
    _: CurrentUser = Depends(require("dashboard:read")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"sla_compliance_pct": await metrics.sla_compliance(session)}
