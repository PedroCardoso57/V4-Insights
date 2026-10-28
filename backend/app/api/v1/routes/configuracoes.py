"""Chaves dos apps das plataformas (Google, Meta, LinkedIn, TikTok), somente admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core import chaves
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Papel
from app.schemas import CampoChaveOut, ChavesIn, GrupoChavesOut
from app.services.audit import registrar

router = APIRouter(prefix="/configuracoes", tags=["configuracoes"])


def _grupos() -> list[GrupoChavesOut]:
    env = get_settings()
    banco = chaves.valores_banco()
    saida: list[GrupoChavesOut] = []
    for g in chaves.GRUPOS:
        campos: list[CampoChaveOut] = []
        for c in g.campos:
            valor = banco.get(c.chave) or getattr(env, c.chave, None) or None
            origem = "sistema" if banco.get(c.chave) else ("env" if valor else None)
            campos.append(
                CampoChaveOut(
                    chave=c.chave,
                    rotulo=c.rotulo,
                    secreto=c.secreto,
                    obrigatorio=c.obrigatorio,
                    origem=origem,
                    valor=None if c.secreto else valor,
                )
            )
        saida.append(
            GrupoChavesOut(
                id=g.id,
                nome=g.nome,
                redirect_uri=f"{env.api_v1_url}{g.callback}",
                configurado=all(c.origem for c in campos if c.obrigatorio),
                campos=campos,
            )
        )
    return saida


@router.get("/chaves", response_model=list[GrupoChavesOut])
def listar_chaves(
    principal: Principal = Depends(require_roles(Papel.admin)),
) -> list[GrupoChavesOut]:
    return _grupos()


@router.put("/chaves", response_model=list[GrupoChavesOut])
def salvar_chaves(
    body: ChavesIn,
    request: Request,
    principal: Principal = Depends(require_roles(Papel.admin)),
    db: Session = Depends(get_db),
) -> list[GrupoChavesOut]:
    """Grava as chaves informadas (cifradas). Valor vazio remove a chave cadastrada e volta a
    valer o `.env`. Os valores nunca são registrados na auditoria, só quais mudaram."""
    try:
        alteradas = chaves.salvar(db, body.valores, principal.usuario.id)
    except KeyError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Chave desconhecida: {exc}"
        ) from exc
    if alteradas:
        registrar(
            db,
            usuario_id=principal.usuario.id,
            acao="alterar_chaves",
            entidade="configuracao",
            dados={"chaves": alteradas},
            request=request,
        )
    db.commit()
    chaves.limpar_cache()
    return _grupos()
