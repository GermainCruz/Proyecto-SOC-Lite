"""Contratos de entrada/salida (Pydantic v2)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.functional_validators import BeforeValidator


Severity = Literal["critical", "high", "medium", "low", "info"]
AlertState = Literal["pending", "triaged", "in_review", "escalated", "closed", "suppressed", "false_positive"]
Verdict = Literal["true_positive", "suspicious", "benign", "false_positive"]
IncidentState = Literal["open", "investigating", "contained", "eradicated", "recovered", "closed"]
AuditResult = Literal["success", "denied", "error"]
IPStr = Annotated[str | None, BeforeValidator(lambda v: str(v) if v is not None else None)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --------------------------------------------------------------------- Auth
class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    otp: str | None = Field(default=None, min_length=6, max_length=6)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class MeOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    permissions: list[str]
    area: str | None = None


# --------------------------------------------------------------------- Users
class RoleOut(ORMModel):
    id: int
    code: str
    name: str
    description: str | None = None


class PermissionOut(ORMModel):
    id: int
    code: str
    module: str
    action: str
    description: str | None = None


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    area: str | None = None
    is_active: bool
    mfa_enabled: bool
    last_login_at: datetime | None = None
    created_at: datetime
    role: RoleOut


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role_code: str
    area: str | None = Field(default=None, max_length=80)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    role_code: str | None = None
    area: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


# --------------------------------------------------------------------- Alerts
class AssetOut(ORMModel):
    id: uuid.UUID
    name: str
    hostname: str | None = None
    ip_address: IPStr = None
    kind: str
    criticality: Severity
    owner_area: str | None = None


class TriageOut(ORMModel):
    id: uuid.UUID
    model: str
    prompt_version: str
    suggested_severity: Severity
    verdict: Verdict
    confidence: float | None = None
    summary: str
    recommended_actions: list[Any] = []
    mitre_techniques: list[str] = []
    needs_human_review: bool
    human_verdict: Verdict | None = None
    reviewed_at: datetime | None = None
    latency_ms: int | None = None
    created_at: datetime


class EnrichmentOut(ORMModel):
    provider: str
    indicator: str
    indicator_type: str
    verdict: str | None = None
    score: Decimal | None = None
    raw: dict[str, Any] = {}
    fetched_at: datetime


class AlertOut(ORMModel):
    id: uuid.UUID
    external_id: str | None = None
    title: str
    description: str | None = None
    severity: Severity
    status: AlertState
    assigned_to: uuid.UUID | None = None
    rule_id: str | None = None
    rule_level: int | None = None
    src_ip: IPStr = None
    dst_ip: IPStr = None
    dst_port: int | None = None
    protocol: str | None = None
    agent_name: str | None = None
    dedup_count: int
    mitre_tactic: str | None = None
    mitre_technique: str | None = None
    source: str | None = None
    asset: AssetOut | None = None
    latest_triage: TriageOut | None = None
    created_at: datetime
    first_seen_at: datetime
    last_seen_at: datetime

    @field_validator("source", mode="before")
    @classmethod
    def source_code(cls, value: Any) -> Any:
        # El ORM entrega un objeto AlertSource; se expone solo el código
        return getattr(value, "code", value)


class AlertDetail(AlertOut):
    raw_payload: dict[str, Any] = {}
    triage_results: list[TriageOut] = []
    enrichments: list[EnrichmentOut] = []
    incident_code: str | None = None


class AlertUpdate(BaseModel):
    status: AlertState | None = None
    severity: Severity | None = None
    assigned_to: uuid.UUID | None = None
    comment: str | None = Field(default=None, max_length=500)


class AlertCreate(BaseModel):
    title: str = Field(min_length=5, max_length=240)
    description: str | None = None
    severity: Severity = "medium"
    rule_id: str | None = Field(default=None, max_length=32)
    src_ip: IPStr = None
    dst_ip: IPStr = None
    agent_name: str | None = Field(default=None, max_length=120)
    raw_payload: dict[str, Any] = {}


class AlertPage(BaseModel):
    items: list[AlertOut]
    total: int
    page: int
    page_size: int
    pages: int


class TriageReview(BaseModel):
    verdict: Verdict
    comment: str = Field(min_length=5, max_length=500)


# --------------------------------------------------------------------- Incidents
class IncidentOut(ORMModel):
    id: uuid.UUID
    code: str
    title: str
    severity: Severity
    status: IncidentState
    sla_due_at: datetime
    opened_at: datetime
    closed_at: datetime | None = None
    resolution: str | None = None
    ticket_system: str | None = None
    ticket_ref: str | None = None
    assigned_to: uuid.UUID | None = None


class IncidentCreate(BaseModel):
    title: str = Field(min_length=5, max_length=240)
    severity: Severity = "high"
    alert_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None


class IncidentUpdate(BaseModel):
    status: IncidentState | None = None
    assigned_to: uuid.UUID | None = None
    resolution: str | None = Field(default=None, max_length=4000)
    ticket_ref: str | None = None


# --------------------------------------------------------------------- Dashboard
class KpiSet(BaseModel):
    open_alerts: int
    open_critical: int
    mttt_minutes: float | None
    fp_rate_pct: float | None
    avg_confidence: float | None
    sla_breached: int
    auto_triage_pct: float | None
    mttr_minutes: float | None
    alerts_today: int
    alerts_delta_pct: float | None


class SeriesPoint(BaseModel):
    label: str
    value: float


class SeverityBucket(BaseModel):
    severity: Severity
    count: int


class DashboardOut(BaseModel):
    kpis: KpiSet
    daily_volume: list[SeriesPoint]
    by_severity: list[SeverityBucket]
    by_source: list[SeriesPoint]
    top_sources_ip: list[SeriesPoint]
    aging_buckets: list[SeriesPoint]
    sla_compliance_pct: float | None
    generated_at: datetime


# --------------------------------------------------------------------- Reports
class ReportRequest(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    kind: Literal["operational", "management", "executive"] = "operational"
    format: Literal["pdf", "docx", "xlsx"] = "pdf"
    period_start: date
    period_end: date
    filters: dict[str, Any] = {}

    @field_validator("period_end")
    @classmethod
    def validate_period(cls, value: date, info) -> date:
        start = info.data.get("period_start")
        if start and value < start:
            raise ValueError("period_end no puede ser anterior a period_start")
        return value


class ReportOut(ORMModel):
    id: uuid.UUID
    code: str
    title: str
    kind: str
    format: str
    period_start: date
    period_end: date
    status: str
    file_size: int | None = None
    created_at: datetime


# --------------------------------------------------------------------- Audit
class AuditOut(ORMModel):
    id: int
    occurred_at: datetime
    user_email: str | None = None
    role_code: str | None = None
    action: str
    module: str
    entity: str | None = None
    entity_id: str | None = None
    result: str
    ip_address: IPStr = None
    request_id: uuid.UUID | None = None
    detail: dict[str, Any] = {}


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int
    page: int
    page_size: int


class ChainVerification(BaseModel):
    total: int
    broken: int
    intact: bool
    checked_at: datetime


# --------------------------------------------------------------------- Misc
class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: bool
    ai_service: bool
    checked_at: datetime


PageNumber = Annotated[int, Field(ge=1, le=10_000)]
