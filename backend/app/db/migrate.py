"""Aplica migrations com segurança em base limpa ou já inicializada pela baseline SQL.

    python -m app.db.migrate            # upgrade head
    python -m app.db.migrate --check    # só informa o estado

- Base limpa: `alembic upgrade head` (0001 executa a baseline, 0002 os ajustes).
- Base inicializada manualmente com `001_initial.sql` (sem `alembic_version`): valida que
  TODAS as tabelas e perfis da baseline existem, registra `stamp 0001` sem reaplicar o SQL
  e segue para `head`. Base parcial é recusada para intervenção manual.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[2]
BASELINE_TABLES = {
    "perfis",
    "usuarios",
    "clientes",
    "usuarios_clientes",
    "integracoes",
    "contas_anuncio",
    "metricas_diarias",
    "dashboards",
    "dashboard_widgets",
    "relatorios",
    "relatorio_execucoes",
    "auditoria",
}
PERFIS = {"admin", "gestor", "analista", "visualizador"}


class EstadoInvalido(RuntimeError):
    pass


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def diagnosticar(url: str) -> str:
    """Retorna 'limpa', 'baseline' ou 'versionada'; levanta EstadoInvalido se parcial."""
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            tabelas = set(inspect(conn).get_table_names())
            if "alembic_version" in tabelas:
                return "versionada"
            presentes = tabelas & BASELINE_TABLES
            if not presentes:
                return "limpa"
            faltando = BASELINE_TABLES - presentes
            if faltando:
                raise EstadoInvalido(
                    "Base parcialmente inicializada; tabelas ausentes: "
                    + ", ".join(sorted(faltando))
                )
            perfis = set(conn.execute(text("SELECT codigo FROM perfis")).scalars())
            if not perfis >= PERFIS:
                raise EstadoInvalido("Tabela perfis não contém os quatro perfis da baseline")
            return "baseline"
    finally:
        engine.dispose()


def migrar(url: str) -> str:
    estado = diagnosticar(url)
    cfg = _config(url)
    if estado == "baseline":
        command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")
    return estado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.db.migrate")
    parser.add_argument("--check", action="store_true", help="apenas diagnostica")
    args = parser.parse_args(argv)
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL não definido", file=sys.stderr)
        return 2
    try:
        if args.check:
            print(f"estado: {diagnosticar(url)}")
            return 0
        estado = migrar(url)
    except EstadoInvalido as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    print(f"migrations aplicadas (estado inicial: {estado})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
