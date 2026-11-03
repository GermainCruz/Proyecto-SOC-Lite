"""Modelo de datos ORM (SQLAlchemy 2.0, mapeo explícito al esquema soc)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

metadata = MetaData(schema="soc")


def pg_enum(name: str, *values: str) -> Enum:
    """Mapea un ENUM nativo de PostgreSQL ya creado por el DDL (create_type=False)."""
    return Enum(*values, name=name, schema="soc", create_type=False, native_enum=True)


SeverityLevel = pg_enum("severity_level", "critical", "high", "medium", "low", "info")
AlertStatus = pg_enum(
    "alert_status", "pending", "triaged", "in_review", "escalated", "closed",
    "suppressed", "false_positive",
)
TriageVerdict = pg_enum("triage_verdict", "true_positive", "suspicious", "benign", "false_positive")
IncidentStatus = pg_enum(
    "incident_status", "open", "investigating", "contained", "eradicated", "recovered", "closed",
)
ReportFormat = pg_enum("report_format", "pdf", "docx", "xlsx")
AuditResult = pg_enum("audit_result", "success", "denied", "error")


class Base(DeclarativeBase):
    metadata = metadata


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    module: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("soc.roles.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("soc.permissions.id"), primary_key=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role_id: Mapped[int] = mapped_column(ForeignKey("soc.roles.id"))
    area: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(Text)
    failed_attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("soc.users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    hostname: Mapped[str | None] = mapped_column(String(120))
    ip_address: Mapped[str | None] = mapped_column(INET)
    kind: Mapped[str] = mapped_column(String(32))
    criticality: Mapped[str] = mapped_column(String(16), default="medium")
    owner_area: Mapped[str | None] = mapped_column(String(80))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertSource(Base):
    __tablename__ = "alert_sources"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(32))
    endpoint: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("soc.alert_sources.id"))
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("soc.assets.id"))
    rule_id: Mapped[str | None] = mapped_column(String(32))
    rule_level: Mapped[int | None] = mapped_column(SmallInteger)
    severity: Mapped[str] = mapped_column(SeverityLevel, default="medium")
    status: Mapped[str] = mapped_column(AlertStatus, default="pending")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("soc.users.id"), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)
    src_ip: Mapped[str | None] = mapped_column(INET)
    dst_ip: Mapped[str | None] = mapped_column(INET)
    src_port: Mapped[int | None] = mapped_column(Integer)
    dst_port: Mapped[int | None] = mapped_column(Integer)
    protocol: Mapped[str | None] = mapped_column(String(16))
    username: Mapped[str | None] = mapped_column(String(80))
    agent_name: Mapped[str | None] = mapped_column(String(120))
    dedup_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    mitre_tactic: Mapped[str | None] = mapped_column(String(80))
    mitre_technique: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[AlertSource] = relationship(lazy="joined")
    asset: Mapped[Asset | None] = relationship(lazy="joined")
    triage_results: Mapped[list["TriageResult"]] = relationship(
        back_populates="alert", order_by="TriageResult.created_at.desc()"
    )
    enrichments: Mapped[list["Enrichment"]] = relationship(back_populates="alert")

    @property
    def latest_triage(self) -> "TriageResult | None":
        """Último triaje para la vista de bandeja (evita N+1 en el frontend)."""
        return self.triage_results[0] if self.triage_results else None


class Enrichment(Base):
    __tablename__ = "enrichment_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("soc.alerts.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(32))
    indicator: Mapped[str] = mapped_column(Text)
    indicator_type: Mapped[str] = mapped_column(String(16))
    verdict: Mapped[str | None] = mapped_column(String(32))
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    ttl_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    error: Mapped[str | None] = mapped_column(Text)

    alert: Mapped[Alert] = relationship(back_populates="enrichments")


class TriageResult(Base):
    __tablename__ = "triage_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("soc.alerts.id", ondelete="CASCADE"))
    engine: Mapped[str] = mapped_column(String(32), default="langchain")
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(16), default="v1.2")
    suggested_severity: Mapped[str] = mapped_column(SeverityLevel)
    verdict: Mapped[str] = mapped_column(TriageVerdict)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    summary: Mapped[str] = mapped_column(Text)
    recommended_actions: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    mitre_techniques: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    human_verdict: Mapped[str | None] = mapped_column(TriageVerdict)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    alert: Mapped[Alert] = relationship(back_populates="triage_results")


class SlaPolicy(Base):
    __tablename__ = "sla_policies"

    severity: Mapped[str] = mapped_column(SeverityLevel, primary_key=True)
    ack_minutes: Mapped[int] = mapped_column(Integer)
    resolve_minutes: Mapped[int] = mapped_column(Integer)
    notify_channel: Mapped[str] = mapped_column(String(32), default="slack")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    title: Mapped[str] = mapped_column(String(240))
    severity: Mapped[str] = mapped_column(SeverityLevel)
    status: Mapped[str] = mapped_column(IncidentStatus, default="open")
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("soc.assets.id"))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("soc.users.id"))
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    ticket_system: Mapped[str | None] = mapped_column(String(32))
    ticket_ref: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncidentAlert(Base):
    __tablename__ = "incident_alerts"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("soc.incidents.id", ondelete="CASCADE"), primary_key=True
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("soc.alerts.id", ondelete="CASCADE"), primary_key=True
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_email: Mapped[str | None] = mapped_column(CITEXT)
    role_code: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64))
    module: Mapped[str] = mapped_column(String(32))
    entity: Mapped[str | None] = mapped_column(String(48))
    entity_id: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(AuditResult, default="success")
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    row_hash: Mapped[str | None] = mapped_column(String(64))


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(32))
    format: Mapped[str] = mapped_column(ReportFormat)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    file_path: Mapped[str | None] = mapped_column(Text)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    checksum: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    generated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))




