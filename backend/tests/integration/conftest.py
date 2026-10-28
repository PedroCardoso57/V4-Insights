"""Fixtures de integração: banco PostgreSQL e Redis reais (TEST_DATABASE_URL)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import chaves
from app.db.session import Base, get_engine, get_sessionmaker
from app.main import app
from app.models import Cliente, Usuario, UsuarioCliente
from app.workers import queue

ORIGIN = "http://localhost:5173"
API_V1 = "/api/v1"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


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
    # `perfis` contém os dados de referência da baseline e não é limpa.
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables if t.name != "perfis")
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    # Contadores de rate limit e deduplicação de alertas não vazam entre testes.
    r = queue.get_redis()
    for k in r.scan_iter("v4:*"):
        r.delete(k)
    chaves.limpar_cache()


class Fila:
    """Captura tarefas enviadas ao Celery para execução controlada nos testes."""

    def __init__(self) -> None:
        self.sync: list[tuple[uuid.UUID, float | None]] = []
        self.relatorio: list[tuple[uuid.UUID, float | None]] = []

    def __call__(self, tarefa: str, objeto_id: uuid.UUID, delay: float | None) -> None:
        destino = self.sync if tarefa == queue.SYNC else self.relatorio
        destino.append((objeto_id, delay))


@pytest.fixture
def fila() -> Iterator[Fila]:
    f = Fila()
    queue.set_enqueue_override(f)
    yield f
    queue.set_enqueue_override(None)


@pytest.fixture
def enfileirados(fila: Fila) -> list[tuple[uuid.UUID, float | None]]:
    return fila.sync


@pytest.fixture
def db() -> Iterator[Session]:
    s = get_sessionmaker()()
    yield s
    s.close()


class ApiClient(TestClient):
    """TestClient autenticado que envia Origin e X-CSRF-Token automaticamente."""

    csrf: str | None = None

    def request(self, method: str, url: Any, **kw: Any) -> Any:  # type: ignore[override]
        # Rotas de negócio vivem em /api/v1; os testes usam caminhos relativos a ele.
        if (
            isinstance(url, str)
            and url.startswith("/")
            and not url.startswith(("/api/", "/health", "/openapi.json", "/docs", "/metrics"))
        ):
            url = API_V1 + url
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
            from app.services.perfis import perfil_id

            u = Usuario(
                nome=f"Usuário {papel}",
                email=email or f"{uuid.uuid4().hex[:8]}@v4.com",
                perfil_id=perfil_id(db, papel),
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
            token, csrf, _ = create_session(db, usuario.id, req)
            db.commit()
            c = ApiClient(app)
            c.cookies.set("v4_session", token)
            c.csrf = csrf
            return c

    return F()
