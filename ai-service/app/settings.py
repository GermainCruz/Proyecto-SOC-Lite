"""Configuración del microservicio de triaje."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SOC-Lite Triage Service"
    service_token: str = "change-me"
    log_level: str = "INFO"

    # LLM: Ollama local por defecto (no se exfiltran alertas)
    llm_provider: str = "ollama"           # ollama | openai
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b-instruct-q4_K_M"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    temperature: float = 0.0
    max_tokens: int = 900
    request_timeout: float = 75.0
    max_agent_iterations: int = 6

    # Enriquecimiento externo (opcional; se degrada a "unknown" si falta la clave)
    virustotal_api_key: str | None = None
    abuseipdb_api_key: str | None = None
    geoip_api_url: str | None = None
    nvd_api_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    backend_api_url: str = "http://backend:8000/api/v1"

    prompt_version: str = "v1.3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
