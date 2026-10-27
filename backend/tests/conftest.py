"""Ambiente de teste: definido antes de importar a aplicação (configuração validada no import)."""

from __future__ import annotations

import os
import tempfile

from cryptography.fernet import Fernet

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL", "postgresql+psycopg://v4:v4@localhost:5432/v4insights_test"
    ),
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["GOOGLE_OIDC_CLIENT_ID"] = "client-id-teste"
os.environ["GOOGLE_OIDC_CLIENT_SECRET"] = "client-secret-teste"
os.environ["COOKIE_SECURE"] = "false"
os.environ["FRONTEND_URL"] = "http://localhost:5173"
os.environ["API_BASE_URL"] = "http://testserver"
os.environ["META_APP_ID"] = "meta-app"
os.environ["META_APP_SECRET"] = "meta-secret"
os.environ["LINKEDIN_CLIENT_ID"] = "linkedin-app"
os.environ["LINKEDIN_CLIENT_SECRET"] = "linkedin-secret"
os.environ["TIKTOK_APP_ID"] = "tiktok-app"
os.environ["TIKTOK_APP_SECRET"] = "tiktok-secret"
os.environ["REPORTS_STORAGE_DIR"] = tempfile.mkdtemp(prefix="v4-relatorios-")
