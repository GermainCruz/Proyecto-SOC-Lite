"""API del microservicio de triaje (LangChain + FastAPI)."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.agent import TriageOutput, run_triage
from app.settings import get_settings
from app.tools import gather_evidence

settings = get_settings()
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger("triage-service")

app = FastAPI(
    title="SOC-Lite Triage Service",
    version="1.3.0",
    description="Triaje de alertas SOC con enriquecimiento y razonamiento LLM (LangChain).",
)


class AlertIn(BaseModel):
    alert_id: str | None = None
    title: str
    description: str | None = None
    severity: str = "medium"
    rule_id: str | None = None
    rule_level: int | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    username: str | None = None
    agent_name: str | None = None
    mitre_tactic: str | None = None
    mitre_technique: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ContextIn(BaseModel):
    asset_criticality: str = "medium"
    historical_false_positive_rate: float = 0.2
    recent_alerts: list[dict[str, Any]] = Field(default_factory=list)


class TriageRequest(BaseModel):
    alert_id: str | None = None
    alert: AlertIn
    context: ContextIn = Field(default_factory=ContextIn)


class TriageResponse(TriageOutput):
    alert_id: str
    engine: str
    model: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float


def verify_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")
    if authorization.removeprefix("Bearer ").strip() != settings.service_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido")


@app.get("/health", tags=["Operación"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "model": settings.ollama_model if settings.llm_provider == "ollama" else settings.openai_model,
        "prompt_version": settings.prompt_version,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/triage", response_model=TriageResponse, dependencies=[Depends(verify_token)], tags=["Triaje"])
async def triage(payload: TriageRequest) -> TriageResponse:
    started = time.perf_counter()
    body = payload.model_dump()
    if payload.alert_id and not body["alert"].get("alert_id"):
        body["alert"]["alert_id"] = payload.alert_id

    try:
        result = await asyncio.wait_for(run_triage(body), timeout=settings.request_timeout + 10)
    except asyncio.TimeoutError as exc:
        logger.error("triage_timeout", alert_id=payload.alert_id)
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Triaje excedió el tiempo límite") from exc

    logger.info(
        "triage_completed",
        alert_id=payload.alert_id,
        verdict=result["verdict"],
        severity=result["suggested_severity"],
        confidence=result["confidence"],
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    return TriageResponse(**result)


@app.post("/api/v1/enrich", dependencies=[Depends(verify_token)], tags=["Enriquecimiento"])
async def enrich(alert: AlertIn) -> dict[str, Any]:
    """Enriquecimiento puro sin LLM (útil para el dashboard y para pruebas)."""
    return await gather_evidence(alert.model_dump())
