"""SPEC-08: migrations em base limpa e em base já inicializada pela baseline SQL."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.db import migrate
from app.db.session import get_engine

BASELINE = Path(__file__).resolve().parents[2] / "alembic" / "baseline" / "001_initial.sql"


@pytest.fixture
def url_mig() -> Iterator[str]:
    """Banco descartável, separado do banco de testes da aplicação."""
    base = get_engine().url
    nome = f"{base.database}_mig"
    with get_engine().connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{nome}"'))
        c.execute(text(f'CREATE DATABASE "{nome}"'))
    url = base.set(database=nome).render_as_string(hide_password=False)
    anterior = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url  # alembic/env.py lê daqui
    yield url
    os.environ["DATABASE_URL"] = anterior or ""
    with get_engine().connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'))


def _tabelas(url: str) -> set[str]:
    e = create_engine(url)
    try:
        with e.connect() as c:
            return set(inspect(c).get_table_names())
    finally:
        e.dispose()


def _sql(url: str, sql: str) -> list[tuple[object, ...]]:
    e = create_engine(url)
    try:
        with e.begin() as c:
            r = c.exec_driver_sql(sql)
            return [tuple(x) for x in r] if r.returns_rows else []
    finally:
        e.dispose()


def test_base_limpa_aplica_uma_unica_vez(url_mig: str) -> None:
    assert migrate.diagnosticar(url_mig) == "limpa"
    assert migrate.migrar(url_mig) == "limpa"
    tabelas = _tabelas(url_mig)
    assert {"perfis", "sessoes", "sync_jobs", "credenciais_integracao", "relatorios"} <= tabelas
    assert migrate.migrar(url_mig) == "versionada"  # repetir não duplica nada
    assert _sql(url_mig, "SELECT count(*) FROM perfis") == [(4,)]
    assert _sql(url_mig, "SELECT version_num FROM alembic_version") == [("0003",)]


def test_base_inicializada_pela_baseline_preserva_dados(url_mig: str) -> None:
    _sql(url_mig, BASELINE.read_text())  # como no pacote Sprint 1, aplicado via psql
    _sql(
        url_mig,
        """
        INSERT INTO usuarios(perfil_id, nome, email)
          SELECT id, 'Ana', 'Ana@V4.com' FROM perfis WHERE codigo = 'admin';
        INSERT INTO clientes(nome, status, arquivado_em) VALUES ('Antigo', 'inativo', now());
        INSERT INTO clientes(nome) VALUES ('Atual');
    """,
    )
    assert migrate.diagnosticar(url_mig) == "baseline"
    assert migrate.migrar(url_mig) == "baseline"
    assert _sql(url_mig, "SELECT email FROM usuarios") == [("Ana@V4.com",)]
    assert sorted(_sql(url_mig, "SELECT nome, status FROM clientes")) == [
        ("Antigo", "arquivado"),
        ("Atual", "ativo"),
    ]
    assert _sql(url_mig, "SELECT count(*) FROM perfis") == [(4,)]  # baseline não reaplicada
    assert "sessoes" in _tabelas(url_mig)


def test_base_parcial_e_recusada(url_mig: str) -> None:
    _sql(url_mig, "CREATE TABLE clientes (id int)")
    with pytest.raises(migrate.EstadoInvalido):
        migrate.migrar(url_mig)


def test_rollback_completo_e_reaplicacao(url_mig: str) -> None:
    from alembic import command

    migrate.migrar(url_mig)
    cfg = migrate._config(url_mig)
    command.downgrade(cfg, "0001")
    assert "sessoes" not in _tabelas(url_mig) and "perfis" in _tabelas(url_mig)
    command.downgrade(cfg, "base")
    assert _tabelas(url_mig) <= {"alembic_version"}
    command.upgrade(cfg, "head")
    assert "sync_jobs" in _tabelas(url_mig)


def test_schema_tem_fks_e_indices(url_mig: str) -> None:
    migrate.migrar(url_mig)
    e = create_engine(url_mig)
    try:
        with e.connect() as c:
            insp = inspect(c)
            fks = {
                (f["referred_table"], tuple(f["constrained_columns"]))
                for f in insp.get_foreign_keys("sync_jobs")
            }
            assert ("integracoes", ("integracao_id",)) in fks
            uniq = {tuple(u["column_names"]) for u in insp.get_unique_constraints("sync_jobs")}
            assert ("integracao_id", "idempotency_key") in uniq
            assert any(
                i["name"] == "ix_auditoria_cliente_data" for i in insp.get_indexes("auditoria")
            )
            sess = {col["name"] for col in insp.get_columns("sessoes")}
            assert "token_hash" in sess and "token" not in sess
    finally:
        e.dispose()
