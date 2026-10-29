"""Atendimento a titulares (LGPD) para dados de colaboradores.

Os titulares de dados pessoais no sistema são os colaboradores (nome, e-mail, foto, vínculo
Google, IP/user-agent de sessões e trilha de auditoria). Clientes são pessoas jurídicas/negócios;
CPF opcional de cliente pessoa física é tratado como dado pessoal e pode ser removido pela edição
do cliente.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Auditoria, Cliente, Sessao, Usuario, UsuarioCliente, UsuarioFoto
from app.services.audit import registrar


class TitularNaoEncontrado(LookupError):
    pass


def _usuario(db: Session, email: str) -> Usuario:
    u = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email.strip().lower()))
    if u is None:
        raise TitularNaoEncontrado(email)
    return u


def exportar(db: Session, email: str) -> dict[str, Any]:
    """Relatório dos dados pessoais mantidos sobre o colaborador (direito de acesso)."""
    u = _usuario(db, email)
    sessoes = db.scalars(select(Sessao).where(Sessao.usuario_id == u.id)).all()
    clientes = db.execute(
        select(Cliente.id, Cliente.nome)
        .join(UsuarioCliente, UsuarioCliente.cliente_id == Cliente.id)
        .where(UsuarioCliente.usuario_id == u.id)
    ).all()
    eventos = db.scalars(
        select(Auditoria).where(Auditoria.usuario_id == u.id).order_by(Auditoria.data_hora)
    ).all()
    return jsonable_encoder(
        {
            "gerado_em": datetime.now(UTC),
            "usuario": {
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "perfil": u.papel,
                "ativo": u.ativo,
                "vinculado_google": u.google_sub is not None,
                "tem_senha": u.senha_hash is not None,
                "tem_foto": u.foto_atualizada_em is not None,
                "criado_em": u.criado_em,
                "ultimo_login_em": u.ultimo_login_em,
            },
            "carteira": [{"id": c.id, "nome": c.nome} for c in clientes],
            "sessoes": [
                {
                    "criado_em": s.criado_em,
                    "expira_em": s.expira_em,
                    "revogado_em": s.revogado_em,
                    "ip": s.ip,
                    "user_agent": s.user_agent,
                }
                for s in sessoes
            ],
            "auditoria": [
                {"data_hora": e.data_hora, "acao": e.acao, "entidade": e.entidade, "ip": e.ip}
                for e in eventos
            ],
        }
    )


def anonimizar(db: Session, email: str) -> uuid.UUID:
    """Anonimização pela CLI (atendimento a titular)."""
    u = _usuario(db, email)
    excluir(db, u, ator_id=None, acao="lgpd_anonimizar", dados={"origem": "cli"})
    db.commit()
    return u.id


def excluir(
    db: Session,
    u: Usuario,
    *,
    ator_id: uuid.UUID | None,
    acao: str = "excluir",
    dados: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """Desliga o colaborador e remove dados identificáveis, preservando a integridade
    referencial e a trilha de auditoria (sem nome/e-mail/IP). Não faz commit.

    O e-mail fica livre para um novo cadastro."""
    uid = u.id
    u.nome = "Colaborador removido"
    u.email = f"removido+{uid.hex}@anonimizado.invalid"
    u.google_sub = None
    u.senha_hash = None
    u.foto_atualizada_em = None
    u.ativo = False
    u.excluido_em = func.now()
    db.query(UsuarioFoto).filter(UsuarioFoto.usuario_id == uid).delete()
    db.execute(
        update(Sessao)
        .where(Sessao.usuario_id == uid)
        .values(revogado_em=func.coalesce(Sessao.revogado_em, func.now()), ip=None, user_agent=None)
    )
    db.execute(update(Auditoria).where(Auditoria.usuario_id == uid).values(ip=None))
    db.query(UsuarioCliente).filter(UsuarioCliente.usuario_id == uid).delete()
    registrar(
        db,
        usuario_id=ator_id,
        acao=acao,
        entidade="usuario",
        entidade_id=uid,
        dados=dados,
        request=request,
    )
