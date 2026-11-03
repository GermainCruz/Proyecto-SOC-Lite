"""Cliente del microservicio de triaje LLM y respaldo heurístico.

El dashboard nunca debe quedarse sin triaje: si el microservicio LangChain no
responde, se aplica una heurística determinista basada en nivel de regla,
reputación de IP y criticidad del activo, y se marca `needs_human_review`.
"""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class TriageUnavailable(Exception):
    """El servicio de IA no respondió en el tiempo esperado."""


async def request_triage(payload: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {settings.ai_service_token}",
        "X-Request-Source": "soc-lite-api",
    }
    url = f"{settings.ai_service_url.rstrip('/')}/api/v1/triage"
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            data.setdefault("engine", "langchain")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            logger.warning("triage_request_failed", attempt=attempt + 1, error=str(exc))

    raise TriageUnavailable(str(last_error) if last_error else "sin respuesta")


def heuristic_triage(alert: dict[str, Any], asset_criticality: str = "medium") -> dict[str, Any]:
    """Respaldo sin LLM: score compuesto y veredicto conservador."""
    level = int(alert.get("rule_level") or 0)
    severity = alert.get("severity") or "medium"
    criticality = asset_criticality

    score = level / 15 * 0.55
    score += {"critical": 0.30, "high": 0.20, "medium": 0.10, "low": 0.03, "info": 0.0}[severity]
    score += {"critical": 0.25, "high": 0.15, "medium": 0.05, "low": 0.0}[criticality]
    score = min(round(score, 3), 1.0)

    verdict = "true_positive" if score >= 0.75 else "suspicious" if score >= 0.45 else "benign"
    suggested = (
        "critical" if score >= 0.9 else
        "high" if score >= 0.7 else
        "medium" if score >= 0.45 else
        "low" if score >= 0.25 else "info"
    )

    return {
        "engine": "heuristic",
        "model": "rule-based-v1",
        "prompt_version": "fallback",
        "suggested_severity": suggested,
        "verdict": verdict,
        "confidence": round(min(0.55 + score / 4, 0.9), 3),
        "summary": (
            "Triaje heurístico de contingencia (servicio LLM no disponible). "
            f"Regla {alert.get('rule_id', 'N/D')} de nivel {level} sobre activo de criticidad "
            f"{criticality}; se recomienda validación humana antes de cerrar."
        ),
        "recommended_actions": [
            "Validar manualmente la alerta en el SIEM de origen",
            "Revisar la reputación de la IP de origen",
            "Restablecer el servicio de triaje y re-ejecutar el análisis",
        ],
        "mitre_techniques": [alert["mitre_technique"]] if alert.get("mitre_technique") else [],
        "evidence": {"fallback": True, "rule_level": level, "asset_criticality": criticality},
        "tokens_in": 0,
        "tokens_out": 0,
        "latency_ms": 0,
        "cost_usd": 0.0,
        "needs_human_review": True,
    }
