from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
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

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import Base, get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Cliente, Usuario, UsuarioCliente  # noqa: E402
from app.sync import queue  # noqa: E402

ORIGIN = "http://localhost:5173"
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def enfileirados() -> Iterator[list[tuple[uuid.UUID, float | None]]]:
    items: list[tuple[uuid.UUID, float | None]] = []
    queue.set_enqueue_override(lambda job_id, delay: items.append((job_id, delay)))
    yield items
    queue.set_enqueue_override(None)


@pytest.fixture
def db() -> Iterator[Session]:
    s = get_sessionmaker()()
    yield s
    s.close()


class ApiClient(TestClient):
    """TestClient autenticado que envia Origin e X-CSRF-Token automaticamente."""

    csrf: str | None = None

    def request(self, method: str, url: Any, **kw: Any) -> Any:  # type: ignore[override]
        headers = dict(kw.pop("headers", None) or {})
        headers.setdefault("Origin", ORIGIN)
        if self.csrf:
            headers.setdefault("X-CSRF-Token", self.csrf)
        return super().request(method, url, headers=headers, **kw)


@pytest.fixture
def anon() -> ApiClient:
    return ApiClient(app)


@pytest.fixture
def factory(db: Session):  # type: ignore[no-untyped-def]
    class F:
        def usuario(
            self,
            papel: str = "analista",
            email: str | None = None,
            ativo: bool = True,
            sub: str | None = None,
        ) -> Usuario:
            u = Usuario(
                nome=f"Usuário {papel}",
                email=email or f"{uuid.uuid4().hex[:8]}@v4.com",
                papel=papel,
                ativo=ativo,
                google_sub=sub,
            )
            db.add(u)
            db.commit()
            return u

        def cliente(
            self, nome: str = "Cliente", membros: tuple[Usuario, ...] = (), status: str = "ativo"
        ) -> Cliente:
            c = Cliente(nome=nome, status=status)
            db.add(c)
            db.flush()
            for m in membros:
                db.add(UsuarioCliente(usuario_id=m.id, cliente_id=c.id))
            db.commit()
            return c

        def login(self, usuario: Usuario) -> ApiClient:
            from starlette.requests import Request

            from app.core.sessions import create_session

            req = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})
            token, sessao = create_session(db, usuario.id, req)
            db.commit()
            c = ApiClient(app)
            c.cookies.set("v4_session", token)
            c.csrf = sessao.csrf_token
            return c

    return F()
