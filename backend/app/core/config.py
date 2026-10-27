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

    # LinkedIn Marketing API (app com o produto Advertising API aprovado)
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    linkedin_api_version: str = "202410"  # cabeçalho LinkedIn-Version (AAAAMM)

    # TikTok Business API (Marketing API)
    tiktok_app_id: str | None = None
    tiktok_app_secret: str | None = None
    tiktok_api_version: str = "v1.3"

    # Sincronização
    sync_interval_hours: int = 6
    sync_history_days_default: int = 90
    sync_max_retries: int = 5
    sync_max_concurrency_per_provider: int = 2

    # Rotação da chave de criptografia: chaves antigas (separadas por vírgula) só para
    # decifrar; `python -m app.cli rotacionar-chave` recifra tudo com ENCRYPTION_KEY.
    encryption_keys_previous: list[str] = Field(default_factory=list)

    # Rate limit (SPEC-07): "<requisições>/<segundos>"; vazio desativa.
    rate_limit_login: str = "20/60"
    # Tentativas de senha por e-mail (contra força bruta distribuída em vários IPs).
    rate_limit_login_email: str = "10/900"
    rate_limit_operacoes_caras: str = "10/60"

    # Retenção (LGPD): dados operacionais expurgados automaticamente.
    audit_retention_days: int = 730
    sessions_retention_days: int = 30

    # Alertas (SPEC-07): webhook (Slack/Google Chat/Teams compatível com JSON {"text"}).
    alert_webhook_url: str | None = None
    alert_sync_falhas_consecutivas: int = 3

    # Relatórios (SPEC-05): storage privado local (volume) e retenção dos PDFs.
    reports_storage_dir: str = "/var/lib/v4insights/relatorios"
    reports_retention_days: int = 90

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        return v

    @field_validator("encryption_keys_previous", mode="before")
    @classmethod
    def _split_keys(cls, v: object) -> object:
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
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
        if self.environment == "production":
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE deve ser true em produção")
            urls = {
                "API_BASE_URL": self.api_base_url,
                "FRONTEND_URL": self.frontend_url,
                "GOOGLE_OIDC_AUTHORIZE_URL": self.google_oidc_authorize_url,
                "GOOGLE_OIDC_TOKEN_URL": self.google_oidc_token_url,
                "GOOGLE_OIDC_JWKS_URL": self.google_oidc_jwks_url,
            }
            inseguras = [k for k, v in urls.items() if not v.startswith("https://")]
            if inseguras:
                raise ValueError(f"Em produção use https em: {', '.join(inseguras)}")
        for k in self.encryption_keys_previous:
            self._check_fernet_key(k)
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

    @property
    def linkedin_enabled(self) -> bool:
        return bool(self.linkedin_client_id and self.linkedin_client_secret)

    @property
    def tiktok_enabled(self) -> bool:
        return bool(self.tiktok_app_id and self.tiktok_app_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
