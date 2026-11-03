"""Cadena de triaje: enriquecimiento → LLM → salida estructurada validada."""
from __future__ import annotations

import json
import time
from typing import Any, Literal

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field, field_validator

from app.prompts import HUMAN_PROMPT, JSON_SCHEMA_HINT, PROMPT_VERSION, SYSTEM_PROMPT
from app.settings import get_settings
from app.tools import TOOLS, gather_evidence

logger = structlog.get_logger(__name__)
settings = get_settings()


class TriageOutput(BaseModel):
    verdict: Literal["true_positive", "suspicious", "benign", "false_positive"]
    suggested_severity: Literal["critical", "high", "medium", "low", "info"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=40, max_length=1200)
    recommended_actions: list[str] = Field(min_length=1, max_length=6)
    mitre_techniques: list[str] = Field(default_factory=list)
    needs_human_review: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("recommended_actions")
    @classmethod
    def clean_actions(cls, value: list[str]) -> list[str]:
        cleaned = [action.strip() for action in value if action and action.strip()]
        return cleaned[:6]

    @field_validator("mitre_techniques")
    @classmethod
    def clean_techniques(cls, value: list[str]) -> list[str]:
        return sorted({t.strip().upper() for t in value if t and t.strip().startswith("T")})


def build_llm():
    """Selecciona el proveedor LLM. Ollama por defecto para no exfiltrar alertas."""
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            api_key=settings.openai_api_key,
            timeout=settings.request_timeout,
        )

    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=settings.temperature,
        num_predict=settings.max_tokens,
        timeout=settings.request_timeout,
        format="json",
    )


def build_agent_executor(llm):
    """Variante agéntica: el modelo decide qué herramientas invocar.

    Se conserva para casos con indicadores ambiguos; el flujo por defecto usa
    salida estructurada porque es más determinista y barata en tokens.
    """
    from langchain.agents import AgentExecutor, create_tool_calling_agent

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        max_iterations=settings.max_agent_iterations,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        verbose=False,
    )


def _render_enrichment(evidence: dict[str, Any]) -> str:
    return json.dumps(evidence, ensure_ascii=False, indent=2)[:4000]


def _usage(llm_result: Any) -> tuple[int, int]:
    metadata = getattr(llm_result, "usage_metadata", None) or {}
    response_metadata = getattr(llm_result, "response_metadata", None) or {}
    tokens_in = int(metadata.get("input_tokens") or response_metadata.get("prompt_eval_count") or 0)
    tokens_out = int(metadata.get("output_tokens") or response_metadata.get("eval_count") or 0)
    return tokens_in, tokens_out


async def run_triage(payload: dict[str, Any]) -> dict[str, Any]:
    alert = payload.get("alert", {})
    context = payload.get("context", {})
    alert_id = payload.get("alert_id") or alert.get("alert_id") or "desconocido"

    started = time.perf_counter()
    evidence = await gather_evidence(alert)
    prompt = HUMAN_PROMPT.format(
        alert_id=alert_id,
        title=alert.get("title", "Sin título"),
        description=alert.get("description", ""),
        severity=alert.get("severity", "medium"),
        rule_id=alert.get("rule_id", "N/D"),
        rule_level=alert.get("rule_level", 0),
        agent_name=alert.get("agent_name", "N/D"),
        asset_criticality=context.get("asset_criticality", "medium"),
        src_ip=alert.get("src_ip") or "N/D",
        dst_ip=alert.get("dst_ip") or "N/D",
        username=alert.get("username") or "N/D",
        mitre_tactic=alert.get("mitre_tactic") or "N/D",
        mitre_technique=alert.get("mitre_technique") or "N/D",
        historical_false_positive_rate=context.get("historical_false_positive_rate", 0.2),
        raw_payload=json.dumps(alert.get("raw_payload", {}), ensure_ascii=False)[:2500],
        enrichment=_render_enrichment(evidence),
        recent_alerts=json.dumps(context.get("recent_alerts", []), ensure_ascii=False)[:800],
    )

    llm = build_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT + "\n\nESQUEMA DE SALIDA:\n" + JSON_SCHEMA_HINT),
        HumanMessage(content=prompt),
    ]

    result: TriageOutput | None = None
    tokens_in = tokens_out = 0
    last_error: str | None = None

    for attempt in range(2):
        try:
            if attempt == 0:
                # with_structured_output aprovecha json_mode/function calling del proveedor
                structured_llm = llm.with_structured_output(TriageOutput, include_raw=True)
                raw = await structured_llm.ainvoke(messages)
                if isinstance(raw, dict) and raw.get("parsed"):
                    result = raw["parsed"]
                    tokens_in, tokens_out = _usage(raw.get("raw"))
                    break
                last_error = "salida no parseable"
            else:
                response = await llm.ainvoke(messages)
                tokens_in, tokens_out = _usage(response)
                content = response.content if isinstance(response.content, str) else str(response.content)
                result = TriageOutput.model_validate(JsonOutputParser().parse(content))
                break
        except Exception as exc:  # incluye ValidationError, JSONDecodeError del LLM
            last_error = str(exc)[:300]
            logger.warning("triage_parse_failed", attempt=attempt + 1, error=last_error)

    latency_ms = int((time.perf_counter() - started) * 1000)

    if result is None:
        logger.error("triage_failed_fallback", alert_id=alert_id, error=last_error)
        return fallback_output(alert, context, latency_ms, last_error)

    return {
        "alert_id": alert_id,
        "engine": "langchain",
        "model": settings.openai_model if settings.llm_provider == "openai" else settings.ollama_model,
        "prompt_version": PROMPT_VERSION,
        **result.model_dump(),
        "evidence": {**result.evidence, "tool_evidence": evidence},
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "cost_usd": estimate_cost(tokens_in, tokens_out),
        "needs_human_review": result.needs_human_review or result.confidence < 0.7,
    }


def estimate_cost(tokens_in: int, tokens_out: int) -> float:
    if settings.llm_provider != "openai":
        return 0.0  # inferencia local: coste marginal eléctrico, no facturable por token
    # Precio de referencia gpt-4o-mini (USD por 1K tokens)
    return round(tokens_in / 1000 * 0.00015 + tokens_out / 1000 * 0.0006, 6)


def fallback_output(
    alert: dict[str, Any], context: dict[str, Any], latency_ms: int, error: str | None
) -> dict[str, Any]:
    level = int(alert.get("rule_level") or 0)
    severity = alert.get("severity") or "medium"
    criticality = context.get("asset_criticality", "medium")
    score = min(level / 15 * 0.55 + {"critical": 0.3, "high": 0.2, "medium": 0.1, "low": 0.03}.get(severity, 0.05)
                + {"critical": 0.25, "high": 0.15, "medium": 0.05}.get(criticality, 0.0), 1.0)
    verdict = "true_positive" if score >= 0.75 else "suspicious" if score >= 0.45 else "benign"
    suggested = "critical" if score >= 0.9 else "high" if score >= 0.7 else "medium" if score >= 0.45 else "low"
    return {
        "alert_id": alert.get("alert_id", "desconocido"),
        "engine": "heuristic",
        "model": "fallback-v1",
        "prompt_version": "fallback",
        "verdict": verdict,
        "suggested_severity": suggested,
        "confidence": round(min(0.55 + score / 4, 0.9), 3),
        "summary": (
            "El modelo de lenguaje no pudo completar el triaje; se aplicó la heurística de "
            f"contingencia sobre la regla {alert.get('rule_id', 'N/D')} (nivel {level}). "
            "Se requiere validación humana."
        ),
        "recommended_actions": [
            "Validar la alerta manualmente en el SIEM de origen",
            "Revisar la reputación de los indicadores",
            "Reintentar el triaje cuando el servicio LLM esté disponible",
        ],
        "mitre_techniques": [alert["mitre_technique"]] if alert.get("mitre_technique") else [],
        "needs_human_review": True,
        "evidence": {"fallback": True, "error": error},
        "tokens_in": 0,
        "tokens_out": 0,
        "latency_ms": latency_ms,
        "cost_usd": 0.0,
    }
