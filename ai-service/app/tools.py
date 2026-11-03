"""Herramientas de enriquecimiento expuestas al agente LangChain.

Todas las funciones devuelven JSON serializable y degradan a {"status": "unavailable"}
cuando falta la clave de API, para que el agente razone con la evidencia disponible
en lugar de fallar.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from langchain_core.tools import tool

from app.settings import get_settings

settings = get_settings()

MITRE_INDEX: dict[str, dict[str, str]] = {
    "T1110": {"name": "Brute Force", "tactic": "Credential Access"},
    "T1078": {"name": "Valid Accounts", "tactic": "Initial Access / Persistence"},
    "T1190": {"name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
    "T1059": {"name": "Command and Scripting Interpreter", "tactic": "Execution"},
    "T1059.001": {"name": "PowerShell", "tactic": "Execution"},
    "T1204": {"name": "User Execution", "tactic": "Execution"},
    "T1204.002": {"name": "Malicious File", "tactic": "Execution"},
    "T1136": {"name": "Create Account", "tactic": "Persistence"},
    "T1098": {"name": "Account Manipulation", "tactic": "Persistence"},
    "T1053": {"name": "Scheduled Task/Job", "tactic": "Persistence"},
    "T1053.003": {"name": "Cron", "tactic": "Persistence"},
    "T1548": {"name": "Abuse Elevation Control Mechanism", "tactic": "Privilege Escalation"},
    "T1014": {"name": "Rootkit", "tactic": "Defense Evasion"},
    "T1562.001": {"name": "Disable or Modify Tools", "tactic": "Defense Evasion"},
    "T1071.004": {"name": "DNS", "tactic": "Command and Control"},
    "T1046": {"name": "Network Service Discovery", "tactic": "Discovery"},
    "T1021.002": {"name": "SMB/Windows Admin Shares", "tactic": "Lateral Movement"},
    "T1048.003": {"name": "Exfiltration Over Unencrypted Non-C2 Protocol", "tactic": "Exfiltration"},
    "T1052.001": {"name": "Exfiltration over USB", "tactic": "Exfiltration"},
    "T1486": {"name": "Data Encrypted for Impact", "tactic": "Impact"},
    "T1566": {"name": "Phishing", "tactic": "Initial Access"},
    "T1566.002": {"name": "Spearphishing Link", "tactic": "Initial Access"},
    "T1133": {"name": "External Remote Services", "tactic": "Initial Access"},
    "T1595": {"name": "Active Scanning", "tactic": "Reconnaissance"},
    "T1499": {"name": "Endpoint Denial of Service", "tactic": "Impact"},
}


def _brief(data: Any, limit: int = 900) -> str:
    text = json.dumps(data, ensure_ascii=False, default=str)
    return text[:limit]


@tool
async def ip_reputation(ip: str) -> str:
    """Consulta la reputación de una IP en VirusTotal y AbuseIPDB.

    Úsala para cualquier alerta con IP de origen externa. Devuelve veredicto,
    puntuación de abuso, país y propietario del ASN.
    """
    result: dict[str, Any] = {"ip": ip, "virustotal": None, "abuseipdb": None}

    async with httpx.AsyncClient(timeout=12.0) as client:
        if settings.virustotal_api_key:
            try:
                response = await client.get(
                    f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
                    headers={"x-apikey": settings.virustotal_api_key},
                )
                if response.status_code == 200:
                    stats = response.json()["data"]["attributes"]["last_analysis_stats"]
                    result["virustotal"] = {
                        "malicious": stats.get("malicious", 0),
                        "suspicious": stats.get("suspicious", 0),
                        "harmless": stats.get("harmless", 0),
                        "country": response.json()["data"]["attributes"].get("country"),
                        "as_owner": response.json()["data"]["attributes"].get("as_owner"),
                    }
                else:
                    result["virustotal"] = {"status": f"http_{response.status_code}"}
            except httpx.HTTPError:
                result["virustotal"] = {"status": "unavailable"}
        else:
            result["virustotal"] = {"status": "not_configured"}

        if settings.abuseipdb_api_key:
            try:
                response = await client.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                    headers={"Key": settings.abuseipdb_api_key, "Accept": "application/json"},
                )
                if response.status_code == 200:
                    data = response.json()["data"]
                    result["abuseipdb"] = {
                        "abuse_confidence": data.get("abuseConfidenceScore"),
                        "total_reports": data.get("totalReports"),
                        "usage_type": data.get("usageType"),
                        "country": data.get("countryCode"),
                    }
                else:
                    result["abuseipdb"] = {"status": f"http_{response.status_code}"}
            except httpx.HTTPError:
                result["abuseipdb"] = {"status": "unavailable"}
        else:
            result["abuseipdb"] = {"status": "not_configured"}

    return _brief(result)


@tool
async def file_hash_lookup(sha256: str) -> str:
    """Consulta un hash SHA-256 en VirusTotal (detecciones y familia de malware)."""
    if not settings.virustotal_api_key:
        return _brief({"hash": sha256, "status": "not_configured"})
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(
                f"https://www.virustotal.com/api/v3/files/{sha256}",
                headers={"x-apikey": settings.virustotal_api_key},
            )
        if response.status_code != 200:
            return _brief({"hash": sha256, "status": f"http_{response.status_code}"})
        attrs = response.json()["data"]["attributes"]
        return _brief({
            "hash": sha256,
            "detections": attrs.get("last_analysis_stats", {}).get("malicious", 0),
            "family": attrs.get("popular_threat_classification", {}).get("suggested_threat_label"),
            "type": attrs.get("type_description"),
        })
    except httpx.HTTPError:
        return _brief({"hash": sha256, "status": "unavailable"})


@tool
async def cve_lookup(cve_id: str) -> str:
    """Obtiene CVSS, descripción y estado KEV de una CVE desde la API del NVD."""
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(settings.nvd_api_url, params={"cveId": cve_id})
        if response.status_code != 200:
            return _brief({"cve": cve_id, "status": f"http_{response.status_code}"})
        vulns = response.json().get("vulnerabilities", [])
        if not vulns:
            return _brief({"cve": cve_id, "status": "not_found"})
        cve = vulns[0]["cve"]
        metrics = cve.get("metrics", {})
        score = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                score = metrics[key][0]["cvssData"].get("baseScore")
                break
        return _brief({
            "cve": cve_id,
            "cvss": score,
            "description": (cve.get("descriptions") or [{}])[0].get("value", "")[:400],
            "kev": "knownExploitedVulnerability" in cve,
            "published": cve.get("published"),
        })
    except httpx.HTTPError:
        return _brief({"cve": cve_id, "status": "unavailable"})


@tool
async def mitre_lookup(technique_id: str) -> str:
    """Devuelve nombre y táctica de una técnica MITRE ATT&CK (índice local)."""
    key = technique_id.strip().upper()
    if key in MITRE_INDEX:
        return _brief({"technique": key, **MITRE_INDEX[key]})
    parent = key.split(".")[0]
    if parent in MITRE_INDEX:
        return _brief({"technique": key, "parent": parent, **MITRE_INDEX[parent]})
    return _brief({"technique": key, "status": "not_indexed"})


@tool
async def geoip_lookup(ip: str) -> str:
    """Geolocaliza una IP (país, ciudad, ASN) usando el servicio configurado."""
    if not settings.geoip_api_url:
        return _brief({"ip": ip, "status": "not_configured"})
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"{settings.geoip_api_url.rstrip('/')}/{ip}")
        if response.status_code != 200:
            return _brief({"ip": ip, "status": f"http_{response.status_code}"})
        data = response.json()
        return _brief({
            "ip": ip,
            "country": data.get("country"),
            "city": data.get("city"),
            "asn": data.get("asn"),
            "org": data.get("org"),
        })
    except httpx.HTTPError:
        return _brief({"ip": ip, "status": "unavailable"})


TOOLS = [ip_reputation, file_hash_lookup, cve_lookup, mitre_lookup, geoip_lookup]
TOOL_MAP = {tool.name: tool for tool in TOOLS}


async def gather_evidence(alert: dict[str, Any]) -> dict[str, Any]:
    """Enriquecimiento determinista en paralelo antes de invocar al LLM.

    Se ejecuta siempre (aunque el agente decida no usar herramientas) porque
    reduce iteraciones, latencia y coste de tokens.
    """
    tasks: list[asyncio.Future] = []
    labels: list[str] = []

    src = alert.get("src_ip")
    dst = alert.get("dst_ip")
    technique = alert.get("mitre_technique")

    if src:
        tasks.append(ip_reputation.ainvoke(src))
        labels.append(f"reputacion:{src}")
        tasks.append(geoip_lookup.ainvoke(src))
        labels.append(f"geoip:{src}")
    if technique:
        tasks.append(mitre_lookup.ainvoke(technique))
        labels.append(f"mitre:{technique}")

    raw = alert.get("raw_payload") or {}
    candidate_hash = (
        raw.get("data", {}).get("sha256")
        or raw.get("syscheck", {}).get("sha256_after")
        or raw.get("file", {}).get("hash")
    )
    if candidate_hash:
        tasks.append(file_hash_lookup.ainvoke(candidate_hash))
        labels.append(f"hash:{candidate_hash[:12]}")

    if not tasks:
        return {"status": "no_indicators"}

    results = await asyncio.gather(*tasks, return_exceptions=True)
    evidence: dict[str, Any] = {}
    for label, result in zip(labels, results):
        if isinstance(result, Exception):
            evidence[label] = {"status": "error", "detail": str(result)[:120]}
        else:
            try:
                evidence[label] = json.loads(result)
            except (TypeError, ValueError):
                evidence[label] = {"raw": str(result)[:400]}
    return evidence
