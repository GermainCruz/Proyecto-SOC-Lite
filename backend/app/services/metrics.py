"""Consultas agregadas del dashboard (SQL directo, sin ORM, para máximo control)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def kpis(session: AsyncSession) -> dict[str, Any]:
    row = (
        await session.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM soc.alerts
                    WHERE status IN ('pending','triaged','in_review','escalated'))            AS open_alerts,
                  (SELECT count(*) FROM soc.alerts
                    WHERE severity = 'critical'
                      AND status IN ('pending','triaged','in_review','escalated'))           AS open_critical,
                  (SELECT round(avg(EXTRACT(EPOCH FROM (t.created_at - a.created_at)) / 60.0)::numeric, 2)
                     FROM soc.triage_results t JOIN soc.alerts a ON a.id = t.alert_id
                    WHERE t.created_at > now() - interval '7 days')                          AS mttt_minutes,
                  (SELECT round(100.0 * count(*) FILTER (WHERE verdict = 'false_positive')
                                / greatest(count(*), 1), 2)
                     FROM soc.triage_results WHERE created_at > now() - interval '7 days')    AS fp_rate_pct,
                  (SELECT round(avg(confidence)::numeric, 3) FROM soc.triage_results
                    WHERE created_at > now() - interval '7 days')                            AS avg_confidence,
                  (SELECT count(*) FROM soc.incidents
                    WHERE status <> 'closed' AND sla_due_at < now())                          AS sla_breached,
                  (SELECT round(100.0 * count(*) FILTER (WHERE status <> 'pending')
                                / greatest(count(*), 1), 2) FROM soc.alerts
                    WHERE created_at > now() - interval '7 days')                            AS auto_triage_pct,
                  (SELECT round(avg(EXTRACT(EPOCH FROM (closed_at - opened_at)) / 60.0)::numeric, 2)
                     FROM soc.incidents WHERE closed_at IS NOT NULL)                          AS mttr_minutes,
                  (SELECT count(*) FROM soc.alerts WHERE created_at::date = CURRENT_DATE)    AS alerts_today,
                  (SELECT count(*) FROM soc.alerts
                    WHERE created_at::date = CURRENT_DATE - 1)                               AS alerts_yesterday
                """
            )
        )
    ).mappings().one()

    data = dict(row)
    yesterday = data.pop("alerts_yesterday") or 0
    today = data.get("alerts_today") or 0
    data["alerts_delta_pct"] = round(100.0 * (today - yesterday) / yesterday, 1) if yesterday else None
    return data


async def daily_volume(session: AsyncSession, days: int = 14) -> list[dict[str, Any]]:
    rows = await session.execute(
        text(
            """
            WITH serie AS (
                SELECT generate_series(CURRENT_DATE - make_interval(days => :days), CURRENT_DATE, '1 day')::date AS day
            )
            SELECT to_char(s.day, 'DD/MM') AS label,
                   count(a.id)             AS value
              FROM serie s
              LEFT JOIN soc.alerts a ON a.created_at::date = s.day
             GROUP BY s.day
             ORDER BY s.day
            """
        ),
        {"days": days - 1},
    )
    return [{"label": r.label, "value": float(r.value)} for r in rows]


async def by_severity(session: AsyncSession, days: int = 7) -> list[dict[str, Any]]:
    rows = await session.execute(
        text(
            """
            SELECT s.severity::text AS severity, count(a.id) AS count
              FROM (VALUES ('critical'),('high'),('medium'),('low'),('info')) AS s(severity)
              LEFT JOIN soc.alerts a
                     ON a.severity = s.severity::soc.severity_level
                    AND a.created_at > now() - make_interval(days => :days)
             GROUP BY s.severity
             ORDER BY array_position(ARRAY['critical','high','medium','low','info'], s.severity)
            """
        ),
        {"days": days},
    )
    return [{"severity": r.severity, "count": r.count} for r in rows]


async def by_source(session: AsyncSession, days: int = 7) -> list[dict[str, Any]]:
    rows = await session.execute(
        text(
            """
            SELECT s.name AS label, count(a.id) AS value
              FROM soc.alert_sources s
              LEFT JOIN soc.alerts a ON a.source_id = s.id
                    AND a.created_at > now() - make_interval(days => :days)
             GROUP BY s.name
             ORDER BY value DESC
            """
        ),
        {"days": days},
    )
    return [{"label": r.label, "value": float(r.value)} for r in rows]


async def top_origin_ips(session: AsyncSession, limit: int = 5) -> list[dict[str, Any]]:
    rows = await session.execute(
        text(
            """
            SELECT host(src_ip) AS label, count(*) AS value
              FROM soc.alerts
             WHERE src_ip IS NOT NULL
               AND created_at > now() - interval '7 days'
             GROUP BY src_ip
             ORDER BY value DESC
             LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [{"label": r.label, "value": float(r.value)} for r in rows]


async def aging_buckets(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await session.execute(
        text(
            """
            SELECT b.label,
                   count(a.id) AS value
              FROM (VALUES
                    ('< 15 min', 0, 15),
                    ('15-60 min', 15, 60),
                    ('1-4 h', 60, 240),
                    ('4-24 h', 240, 1440),
                    ('> 24 h', 1440, 1000000)
                   ) AS b(label, lo, hi)
              LEFT JOIN soc.alerts a
                     ON a.status IN ('pending','triaged','in_review','escalated')
                    AND EXTRACT(EPOCH FROM (now() - a.created_at)) / 60 BETWEEN b.lo AND b.hi
             GROUP BY b.label, b.lo
             ORDER BY b.lo
            """
        )
    )
    return [{"label": r.label, "value": float(r.value)} for r in rows]


async def sla_compliance(session: AsyncSession) -> float | None:
    row = (
        await session.execute(
            text(
                """
                SELECT round(100.0 * count(*) FILTER (WHERE closed_at IS NOT NULL
                                                       AND closed_at <= sla_due_at)
                             / greatest(count(*) FILTER (WHERE closed_at IS NOT NULL), 1), 2) AS pct
                  FROM soc.incidents
                 WHERE opened_at > now() - interval '30 days'
                """
            )
        )
    ).one()
    return float(row.pct) if row.pct is not None else None


async def dashboard(session: AsyncSession) -> dict[str, Any]:
    return {
        "kpis": await kpis(session),
        "daily_volume": await daily_volume(session, 14),
        "by_severity": await by_severity(session, 7),
        "by_source": await by_source(session, 7),
        "top_sources_ip": await top_origin_ips(session, 5),
        "aging_buckets": await aging_buckets(session),
        "sla_compliance_pct": await sla_compliance(session),
        "generated_at": datetime.now(timezone.utc),
    }
