"""Configuração via variáveis de ambiente, validada na inicialização."""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"

    database_url: str = Field(..., description="postgresql+psycopg://user:pass@host:5432/db")
    redis_url: str = "redis://localhost:6379/0"

    # Origem pública da API (redirect URIs usam {api_base_url}/api/v1/...) e do frontend.
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    allowed_origins: list[str] = Field(default_factory=list)

    # Sessão
    session_cookie_name: str = "v4_session"
    csrf_cookie_name: str = "v4_csrf"
    session_ttl_hours: int = 12
    cookie_secure: bool = True

    # Chave Fernet (base64 urlsafe, 32 bytes) para criptografar tokens de integrações.
    # Fica fora do banco (ambiente/secret manager).
    encryption_key: str

    # Login interno Google (OIDC)
    google_oidc_client_id: str
    google_oidc_client_secret: str
    google_oidc_issuer: str = "https://accounts.google.com"
    google_oidc_authorize_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_oidc_token_url: str = "https://oauth2.googleapis.com/token"  # noqa: S105
    google_oidc_jwks_url: str = "https://www.googleapis.com/oauth2/v3/certs"

    # Meta Marketing API
    meta_app_id: str | None = None
    meta_app_secret: str | None = None
    meta_graph_version: str = "v21.0"

    # Google Ads API (OAuth separado do login interno)
    google_ads_client_id: str | None = None
    google_ads_client_secret: str | None = None
    google_ads_developer_token: str | None = None
    google_ads_login_customer_id: str | None = None
    google_ads_api_version: str = "v18"

    # Sincronização
    sync_interval_hours: int = 6
    sync_history_days_default: int = 90
    sync_max_retries: int = 5
    sync_max_concurrency_per_provider: int = 2

    # Relatórios (SPEC-05): storage privado local (volume) e retenção dos PDFs.
    reports_storage_dir: str = "/var/lib/v4insights/relatorios"
    reports_retention_days: int = 90

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        return v

    @field_validator("encryption_key")
    @classmethod
    def _check_fernet_key(cls, v: str) -> str:
        try:
            raw = base64.urlsafe_b64decode(v.encode())
        except Exception as exc:  # pragma: no cover - mensagem de erro
            raise ValueError("ENCRYPTION_KEY deve ser base64 urlsafe") from exc
        if len(raw) != 32:
            raise ValueError("ENCRYPTION_KEY deve conter 32 bytes (use Fernet.generate_key())")
        return v

    @model_validator(mode="after")
    def _defaults_and_prod_checks(self) -> Settings:
        if not self.allowed_origins:
            self.allowed_origins = [self.frontend_url.rstrip("/")]
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE deve ser true em produção")
        if not 1 <= self.sync_interval_hours <= 168:
            raise ValueError("SYNC_INTERVAL_HOURS deve estar entre 1 e 168")
        return self

    @property
    def api_v1_url(self) -> str:
        return f"{self.api_base_url.rstrip('/')}/api/v1"

    @property
    def meta_enabled(self) -> bool:
        return bool(self.meta_app_id and self.meta_app_secret)

    @property
    def google_ads_enabled(self) -> bool:
        return bool(
            self.google_ads_client_id
            and self.google_ads_client_secret
            and self.google_ads_developer_token
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
