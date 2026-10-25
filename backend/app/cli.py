"""Comandos administrativos.

python -m app.cli criar-admin --email pessoa@empresa.com --nome "Nome"
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import func, select

from app.core.oidc import normalize_email
from app.db.session import get_sessionmaker
from app.models import Papel, Usuario
from app.services.audit import registrar
from app.services.perfis import perfil_id


def criar_admin(email: str, nome: str) -> int:
    db = get_sessionmaker()()
    try:
        email = normalize_email(email)
        u = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email))
        if u is None:
            u = Usuario(email=email, nome=nome, perfil_id=perfil_id(db, Papel.admin), ativo=True)
            db.add(u)
            db.flush()
            acao = "criar"
        else:
            u.perfil_id, u.ativo = perfil_id(db, Papel.admin), True
            acao = "promover_admin"
        registrar(
            db,
            usuario_id=None,
            acao=acao,
            entidade="usuario",
            entidade_id=u.id,
            dados={"email": email, "origem": "cli"},
        )
        db.commit()
        print(f"admin pronto: {email} ({u.id})")
        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("criar-admin", help="cria ou promove um administrador")
    p.add_argument("--email", required=True)
    p.add_argument("--nome", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "criar-admin":
        return criar_admin(args.email, args.nome)
    return 1


if __name__ == "__main__":
    sys.exit(main())
