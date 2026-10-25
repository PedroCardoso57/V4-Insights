"""Comandos administrativos.

python -m app.cli criar-admin --email pessoa@empresa.com --nome "Nome"
python -m app.cli openapi --out ../frontend/openapi.json
python -m app.cli rotacionar-chave                 # após trocar ENCRYPTION_KEY
python -m app.cli revogar-sessoes --email x@y.com  # ou --todas
python -m app.cli lgpd-exportar --email x@y.com --out titular.json
python -m app.cli lgpd-anonimizar --email x@y.com --confirmar
"""

from __future__ import annotations

import argparse
import json
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


def exportar_openapi(destino: str) -> int:
    from app.main import app

    conteudo = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if destino == "-":
        sys.stdout.write(conteudo)
    else:
        with open(destino, "w", encoding="utf-8") as fh:
            fh.write(conteudo)
    return 0


def rotacionar_chave() -> int:
    from app.core.crypto import rotacionar_chaves

    db = get_sessionmaker()()
    try:
        n = rotacionar_chaves(db)
        registrar(
            db,
            usuario_id=None,
            acao="rotacionar_chave",
            entidade="credencial",
            dados={"credenciais": n, "origem": "cli"},
        )
        db.commit()
    finally:
        db.close()
    print(
        f"{n} credencial(is) recifrada(s) com a chave atual. Remova a chave antiga de "
        "ENCRYPTION_KEYS_PREVIOUS após confirmar."
    )
    return 0


def revogar_sessoes(email: str | None, todas: bool) -> int:
    from sqlalchemy import update

    from app.core.sessions import now
    from app.models import Sessao
    from app.services.retencao import linhas

    if not email and not todas:
        print("informe --email ou --todas", file=sys.stderr)
        return 2
    db = get_sessionmaker()()
    try:
        stmt = update(Sessao).where(Sessao.revogado_em.is_(None)).values(revogado_em=now())
        if email:
            u = db.scalar(
                select(Usuario).where(func.lower(Usuario.email) == normalize_email(email))
            )
            if u is None:
                print("usuário não encontrado", file=sys.stderr)
                return 1
            stmt = stmt.where(Sessao.usuario_id == u.id)
        n = linhas(db.execute(stmt))
        registrar(
            db,
            usuario_id=None,
            acao="revogar_sessoes",
            entidade="sessao",
            dados={"email": email, "todas": todas, "quantidade": n, "origem": "cli"},
        )
        db.commit()
    finally:
        db.close()
    print(f"{n} sessão(ões) revogada(s).")
    return 0


def lgpd(acao: str, email: str, destino: str, confirmar: bool) -> int:
    from app.services import lgpd as svc

    db = get_sessionmaker()()
    try:
        if acao == "exportar":
            dados = svc.exportar(db, email)
            conteudo = json.dumps(dados, ensure_ascii=False, indent=2) + "\n"
            if destino == "-":
                sys.stdout.write(conteudo)
            else:
                with open(destino, "w", encoding="utf-8") as fh:
                    fh.write(conteudo)
            registrar(
                db,
                usuario_id=None,
                acao="lgpd_exportar",
                entidade="usuario",
                entidade_id=dados["usuario"]["id"],
                dados={"origem": "cli"},
            )
            db.commit()
            return 0
        if not confirmar:
            print("anonimização é irreversível: repita com --confirmar", file=sys.stderr)
            return 2
        uid = svc.anonimizar(db, email)
        print(f"colaborador {uid} anonimizado e desativado.")
        return 0
    except svc.TitularNaoEncontrado:
        print("usuário não encontrado", file=sys.stderr)
        return 1
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("criar-admin", help="cria ou promove um administrador")
    p.add_argument("--email", required=True)
    p.add_argument("--nome", required=True)
    o = sub.add_parser("openapi", help="exporta o schema OpenAPI (fonte do cliente TypeScript)")
    o.add_argument("--out", default="-", help="arquivo de saída ('-' = stdout)")
    sub.add_parser("rotacionar-chave", help="recifra credenciais com a ENCRYPTION_KEY atual")
    rv = sub.add_parser("revogar-sessoes", help="encerra sessões ativas")
    rv.add_argument("--email")
    rv.add_argument("--todas", action="store_true")
    le = sub.add_parser("lgpd-exportar", help="exporta os dados pessoais de um colaborador")
    le.add_argument("--email", required=True)
    le.add_argument("--out", default="-")
    la = sub.add_parser("lgpd-anonimizar", help="anonimiza e desativa um colaborador")
    la.add_argument("--email", required=True)
    la.add_argument("--confirmar", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "rotacionar-chave":
        return rotacionar_chave()
    if args.cmd == "revogar-sessoes":
        return revogar_sessoes(args.email, args.todas)
    if args.cmd == "lgpd-exportar":
        return lgpd("exportar", args.email, args.out, False)
    if args.cmd == "lgpd-anonimizar":
        return lgpd("anonimizar", args.email, "-", args.confirmar)
    if args.cmd == "criar-admin":
        return criar_admin(args.email, args.nome)
    if args.cmd == "openapi":
        return exportar_openapi(args.out)
    return 1


if __name__ == "__main__":
    sys.exit(main())
