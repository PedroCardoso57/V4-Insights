"""Mapeamento de conversões por cliente (M04).

Cada conta de anúncio escolhe quais ações da plataforma contam como "Conversões", quais
somam em "Valor de conversões" e, na Meta, a janela de atribuição. O mapeamento fica em
`contas_anuncio.mapeamento_conversoes`, e o histórico é recalculado a partir de
`metricas_diarias.conversoes_detalhe`, sem chamar a plataforma de novo.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import EDICAO, Principal, get_principal, require_roles
from app.api.rbac import get_cliente_autorizado
from app.db.session import get_db
from app.integrations.base import to_decimal
from app.models import (
    ContaAnuncio,
    Integracao,
    MetricaDiaria,
    Nivel,
    Plataforma,
    StatusCliente,
    StatusIntegracao,
    TipoJob,
)
from app.schemas import (
    AcaoConversaoOut,
    ConversoesClienteOut,
    ConversoesContaOut,
    MapeamentoConversoes,
    SalvarConversoesOut,
)
from app.services import sync
from app.services.audit import registrar

router = APIRouter(prefix="/clientes/{cliente_id}/conversoes", tags=["conversoes"])

DIAS_ANALISADOS = 30

# Janelas de atribuição que a Meta aceita em `action_attribution_windows`. As de 7 e 28 dias
# por visualização foram descontinuadas pela Meta em 2026. Vazio = padrão da conta.
JANELAS: dict[str, list[str]] = {
    Plataforma.meta_ads.value: ["1d_click", "7d_click", "28d_click", "1d_view"],
}


def _contas(db: Session, cliente_id: uuid.UUID) -> list[tuple[ContaAnuncio, Integracao]]:
    return [
        (c, i)
        for c, i in db.execute(
            select(ContaAnuncio, Integracao)
            .join(Integracao, Integracao.id == ContaAnuncio.integracao_id)
            .where(
                Integracao.cliente_id == cliente_id,
                Integracao.status != StatusIntegracao.revogada.value,
            )
            .order_by(Integracao.plataforma, ContaAnuncio.nome)
        ).all()
    ]


def _acoes(db: Session, conta: ContaAnuncio) -> list[AcaoConversaoOut]:
    """Totais por tipo de ação nos últimos 30 dias (nível campanha, para não contar em dobro)."""
    mapeamento = conta.mapeamento_conversoes or {}
    janela = mapeamento.get("janela") or "value"
    inicio = sync.hoje_conta(conta) - timedelta(days=DIAS_ANALISADOS - 1)
    qtd: dict[str, Decimal] = defaultdict(Decimal)
    val: dict[str, Decimal] = {}
    for detalhe in db.scalars(
        select(MetricaDiaria.conversoes_detalhe).where(
            MetricaDiaria.conta_anuncio_id == conta.id,
            MetricaDiaria.nivel == Nivel.campanha.value,
            MetricaDiaria.data >= inicio,
        )
    ):
        for tipo, janelas in ((detalhe or {}).get("acoes") or {}).items():
            qtd[tipo] += to_decimal((janelas or {}).get(janela))
        for tipo, janelas in ((detalhe or {}).get("valores") or {}).items():
            v = (janelas or {}).get(janela)
            if v is not None:
                val[tipo] = val.get(tipo, Decimal(0)) + to_decimal(v)
    # Ações já mapeadas aparecem mesmo sem dados no período, para poderem ser desmarcadas.
    for tipo in [*(mapeamento.get("action_types") or []), *(mapeamento.get("acao_valor") or [])]:
        qtd.setdefault(tipo, Decimal(0))
    return sorted(
        (AcaoConversaoOut(action_type=t, quantidade=q, valor=val.get(t)) for t, q in qtd.items()),
        key=lambda a: (-a.quantidade, a.action_type),
    )


def _saida(db: Session, conta: ContaAnuncio, integ: Integracao) -> ConversoesContaOut:
    return ConversoesContaOut(
        conta_anuncio_id=conta.id,
        integracao_id=integ.id,
        plataforma=integ.plataforma,
        conta_externa_id=conta.conta_externa_id,
        nome=conta.nome,
        moeda=conta.moeda,
        ativa=conta.ativa,
        mapeamento=MapeamentoConversoes.model_validate(conta.mapeamento_conversoes or {}),
        janelas=JANELAS.get(integ.plataforma, []),
        dias_analisados=DIAS_ANALISADOS,
        acoes=_acoes(db, conta),
    )


@router.get("", response_model=ConversoesClienteOut)
def listar(
    cliente_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> ConversoesClienteOut:
    get_cliente_autorizado(db, principal, cliente_id)
    return ConversoesClienteOut(contas=[_saida(db, c, i) for c, i in _contas(db, cliente_id)])


@router.put("/{conta_anuncio_id}", response_model=SalvarConversoesOut)
def salvar(
    cliente_id: uuid.UUID,
    conta_anuncio_id: uuid.UUID,
    body: MapeamentoConversoes,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> SalvarConversoesOut:
    cliente = get_cliente_autorizado(db, principal, cliente_id)
    if cliente.status == StatusCliente.arquivado.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cliente arquivado")
    par = next(((c, i) for c, i in _contas(db, cliente_id) if c.id == conta_anuncio_id), None)
    if par is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conta não encontrada")
    conta, integ = par

    janelas = JANELAS.get(integ.plataforma, [])
    if body.janela and body.janela not in janelas:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Janela de atribuição não disponível para esta plataforma",
        )
    tipos = list(dict.fromkeys(t.strip() for t in body.action_types if t.strip()))
    novo: dict[str, object] = {"action_types": tipos}
    if body.acao_valor is not None:
        novo["acao_valor"] = list(dict.fromkeys(t.strip() for t in body.acao_valor if t.strip()))
    if body.janela:
        novo["janela"] = body.janela

    antes = dict(conta.mapeamento_conversoes or {})
    linhas = 0
    ressincronizar = False
    if novo != antes:
        conta.mapeamento_conversoes = novo
        db.flush()
        linhas = sync.recalcular_conversoes(db, conta)
        # A janela muda o que a plataforma devolve: o histórico só vale depois de coletar de novo.
        ressincronizar = (antes.get("janela") or None) != (novo.get("janela") or None)
        registrar(
            db,
            usuario_id=principal.usuario.id,
            acao="alterar_mapeamento_conversoes",
            entidade="conta_anuncio",
            entidade_id=conta.id,
            cliente_id=cliente_id,
            dados={"antes": antes, "depois": novo},
            request=request,
        )
    db.commit()

    if ressincronizar and conta.ativa and integ.status == StatusIntegracao.conectada.value:
        fim = sync.hoje_conta(conta)
        inicio = fim - timedelta(days=conta.carga_historica_dias)
        job, criado = sync.criar_job(
            db, conta, TipoJob.historico, inicio, fim, principal.usuario.id
        )
        sync.agendar(db, job, criado)
    else:
        ressincronizar = False
    db.refresh(conta)
    return SalvarConversoesOut(
        conta=_saida(db, conta, integ),
        linhas_recalculadas=linhas,
        ressincronizando=ressincronizar,
    )
