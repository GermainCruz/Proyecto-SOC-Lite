"""Configuración central de SOC-Lite (12-factor, validada con Pydantic)."""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicación
    app_name: str = "SOC-Lite API"
    environment: str = Field(default="dev", pattern="^(dev|staging|prod)$")
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Base de datos
    database_url: str = "postgresql+asyncpg://soc_app:soc_app@db:5432/soclite"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # Seguridad
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    cors_origins: str | list[str] = ["http://localhost:5173", "https://soc.local"]

    # Servicio de IA (LangChain)
    ai_service_url: str = "http://ai-service:8000"
    ai_service_token: str = "change-me"
    ai_timeout_seconds: float = 90.0

    # Reportes
    reports_dir: str = "/var/soclite/reports"
    reports_retention_days: int = 365

    # Integraciones
    n8n_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    slack_critical_channel: str = "#soc-critical"

    @field_validator("cors_origins", mode="after")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
