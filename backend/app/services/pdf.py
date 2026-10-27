"""Renderização do PDF de relatórios (A4) a partir do snapshot congelado na solicitação.

O PDF nunca consulta o banco: usa exatamente os números capturados no snapshot, os mesmos
que o dashboard exibia no horário de corte.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from xml.sax.saxutils import escape

from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ACCENT = colors.HexColor("#d6001c")
MUTED = colors.HexColor("#6b7385")
BORDER = colors.HexColor("#e2e5eb")

KPI_LABEL = {
    "investimento": "Investimento",
    "impressoes": "Impressões",
    "cliques": "Cliques",
    "ctr": "CTR",
    "cpc": "CPC",
    "cpm": "CPM",
    "conversoes": "Conversões",
    "valor_conversoes": "Valor de conversões",
    "cpa": "Custo por conversão",
    "roas": "ROAS",
}
# Rótulos curtos para cabeçalhos de colunas estreitas (sem quebra no meio da palavra).
KPI_CURTO = {
    **KPI_LABEL,
    "investimento": "Invest.",
    "impressoes": "Impr.",
    "conversoes": "Conv.",
    "valor_conversoes": "Valor conv.",
    "cpa": "CPA",
}
GRAFICO = {
    "serie_investimento": ("investimento", "Investimento por período"),
    "serie_cliques": ("cliques", "Cliques por período"),
    "serie_conversoes": ("conversoes", "Conversões por período"),
}
PLATAFORMA = {
    "meta_ads": "Meta Ads",
    "google_ads": "Google Ads",
    "linkedin_ads": "LinkedIn Ads",
    "tiktok_ads": "TikTok Ads",
}


def _num(v: Any, casas: int = 2) -> str:
    s = f"{Decimal(str(v)):,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_kpi(kpi: str, v: Any, moeda: str = "BRL") -> str:
    if v is None:
        return "—"
    simbolo = "R$ " if moeda == "BRL" else f"{moeda} "
    if kpi in ("investimento", "valor_conversoes", "cpc", "cpm", "cpa"):
        return simbolo + _num(v)
    if kpi == "ctr":
        return _num(v) + "%"
    if kpi == "roas":
        return _num(v) + "x"
    if kpi == "conversoes":
        return _num(v)
    return _num(v, 0)


def _data(v: str | date | None) -> str:
    if v is None:
        return "—"
    d = v if isinstance(v, date) else date.fromisoformat(str(v)[:10])
    return d.strftime("%d/%m/%Y")


def _datahora(v: str | datetime | None) -> str:
    if v is None:
        return "—"
    d = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
    return d.strftime("%d/%m/%Y %H:%M UTC")


def _estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "t",
            parent=base["Title"],
            alignment=TA_LEFT,
            fontSize=18,
            textColor=colors.black,
            spaceAfter=2 * mm,
        ),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=9, textColor=MUTED),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontSize=12,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            textColor=ACCENT,
        ),
        "p": ParagraphStyle("p", parent=base["Normal"], fontSize=9.5, leading=13),
        "cel": ParagraphStyle("c", parent=base["Normal"], fontSize=8, leading=10),
    }


def _tabela_estilo(cabecalho: bool = True) -> TableStyle:
    cmds: list[Any] = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if cabecalho:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f3f6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfc")]),
        ]
    return TableStyle(cmds)


def _kpis(dados: dict[str, Any], kpis: list[str], moeda: str, largura: float) -> Table:
    resumo = dados["resumo"]
    atual, var = resumo["atual"], resumo["variacao_percentual"]
    linhas: list[list[Any]] = [["Indicador", "Período", "Anterior", "Variação"]]
    anterior = resumo.get("anterior") or {}
    for k in kpis:
        v = var.get(k)
        linhas.append(
            [
                KPI_LABEL.get(k, k),
                fmt_kpi(k, atual.get(k), moeda),
                fmt_kpi(k, anterior.get(k), moeda) if anterior else "—",
                "—" if v is None else ("+" if Decimal(str(v)) > 0 else "") + _num(v) + "%",
            ]
        )
    t = Table(
        linhas,
        colWidths=[largura * 0.4, largura * 0.22, largura * 0.22, largura * 0.16],
        repeatRows=1,
    )
    t.setStyle(_tabela_estilo())
    return t


def _grafico(serie: dict[str, Any], kpi: str, titulo: str, largura: float) -> Drawing:
    altura = 60 * mm
    d = Drawing(largura, altura)
    pontos = serie.get("pontos") or []
    valores = [(i, float(p["kpis"].get(kpi) or 0)) for i, p in enumerate(pontos)]
    d.add(String(0, altura - 10, titulo, fontSize=9, fillColor=colors.black))
    if len(valores) < 2:
        d.add(
            String(
                0,
                altura / 2,
                "Dados insuficientes para o gráfico no período.",
                fontSize=8,
                fillColor=MUTED,
            )
        )
        return d
    lp = LinePlot()
    lp.x, lp.y = 30, 18
    lp.width, lp.height = largura - 40, altura - 40
    linhas = [valores]
    comp = serie.get("comparacao") or []
    if comp:
        linhas.append([(i, float(p["kpis"].get(kpi) or 0)) for i, p in enumerate(comp)])
    lp.data = linhas
    lp.lines[0].strokeColor = ACCENT
    lp.lines[0].strokeWidth = 1.5
    if comp:
        lp.lines[1].strokeColor = MUTED
        lp.lines[1].strokeDashArray = [3, 2]
    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = max(len(valores) - 1, 1)
    passo = max(1, len(pontos) // 6)
    lp.xValueAxis.valueSteps = list(range(0, len(pontos), passo))
    lp.xValueAxis.labelTextFormat = lambda i: (
        _data(pontos[int(i)]["periodo"])[:5] if int(i) < len(pontos) else ""
    )
    lp.xValueAxis.labels.fontSize = 6
    lp.yValueAxis.labels.fontSize = 6
    # Escala explícita: o eixo sempre contém a maior série (atual ou comparação).
    maximo = max((v for linha in linhas for _, v in linha), default=0.0)
    topo = maximo * 1.15 if maximo > 0 else 1.0
    lp.yValueAxis.valueMin = 0
    lp.yValueAxis.valueMax = topo
    lp.yValueAxis.valueSteps = [topo * i / 4 for i in range(5)]
    lp.yValueAxis.labelTextFormat = lambda v: _num(v, 0) if topo >= 10 else _num(v, 2)
    d.add(lp)
    return d


def _campanhas(
    dados: dict[str, Any],
    kpis: list[str],
    moeda: str,
    largura: float,
    limite: int | None,
    est: dict[str, ParagraphStyle],
) -> LongTable | Paragraph:
    camps = dados.get("campanhas") or []
    if not camps:
        return Paragraph("Nenhuma campanha com dados no período.", est["p"])
    cols = [
        k
        for k in kpis
        if k in ("investimento", "impressoes", "cliques", "ctr", "cpc", "conversoes", "cpa", "roas")
    ][:6]
    # Cabeçalhos como Paragraph: quebram linha em vez de invadir a coluna vizinha.
    cab = ParagraphStyle("cab", parent=est["cel"], fontName="Helvetica-Bold", fontSize=7)
    cab_num = ParagraphStyle("cabn", parent=cab, alignment=2)
    linhas: list[list[Any]] = [
        [
            Paragraph("Campanha", cab),
            Paragraph("Plataforma", cab),
            *[Paragraph(KPI_CURTO[k], cab_num) for k in cols],
        ]
    ]
    for c in camps[:limite] if limite else camps:
        nome = c.get("campanha_nome") or c["campanha_externa_id"]
        linhas.append(
            [
                Paragraph(escape(nome), est["cel"]),  # quebra linha em vez de cortar
                PLATAFORMA.get(c["plataforma"], c["plataforma"]),
                *[fmt_kpi(k, c["kpis"].get(k), moeda) for k in cols],
            ]
        )
    # Colunas monetárias recebem mais espaço (valores como "R$ 12.361,70").
    pesos = [
        1.5 if c in ("investimento", "cpc", "cpa") else 0.8 if c == "ctr" else 1.0 for c in cols
    ]
    larguras = [largura * 0.64 * p / sum(pesos) for p in pesos]
    t = LongTable(
        linhas,
        colWidths=[largura * 0.24, largura * 0.12, *larguras],
        repeatRows=1,
        splitByRow=True,
    )
    t.setStyle(_tabela_estilo())
    return t


def _rodape(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 10 * mm, "V4 Insights — uso interno")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


def renderizar(snapshot: dict[str, Any]) -> bytes:
    """Gera o PDF a partir do snapshot (ver services.relatorios.capturar_snapshot)."""
    est = _estilos()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=snapshot.get("titulo", "Relatório"),
        author="V4 Insights",
    )
    largura = A4[0] - 30 * mm
    dados = snapshot["dados"]
    cfg = snapshot["configuracao"]
    moeda = (dados["resumo"].get("moedas") or ["BRL"])[0]
    kpis: list[str] = cfg["kpis"]
    graficos: list[str] = cfg["graficos"]
    executiva = cfg["template"] == "visao_executiva"

    story: list[Any] = [
        Paragraph(escape(snapshot["titulo"]), est["titulo"]),
        Paragraph(
            f"<b>{escape(snapshot['cliente'])}</b> · "
            f"{'Visão Executiva' if executiva else 'Performance de Campanhas'} · "
            f"Período {_data(snapshot['periodo']['inicio'])} a {_data(snapshot['periodo']['fim'])}",
            est["sub"],
        ),
        Paragraph(
            f"Dados até o corte de {_datahora(snapshot['horario_corte'])} · última coleta "
            f"{_datahora(snapshot.get('ultima_coleta_em'))}",
            est["sub"],
        ),
    ]
    if len(dados["resumo"].get("moedas") or []) > 1:
        story.append(
            Paragraph(
                "Atenção: contas em moedas diferentes somadas sem conversão cambial.", est["sub"]
            )
        )
    story += [Paragraph("Indicadores", est["h2"]), _kpis(dados, kpis, moeda, largura)]
    if "conversoes" in kpis and dados["resumo"]["atual"].get("conversoes") is None:
        story.append(Spacer(1, 2 * mm))
        story.append(
            Paragraph(
                "Conversões, CPA e ROAS ausentes: nenhuma ação de conversão mapeada nas contas.",
                est["sub"],
            )
        )

    for g in graficos:
        if g in GRAFICO and dados.get("serie"):
            kpi, titulo = GRAFICO[g]
            story.append(
                KeepTogether([Spacer(1, 4 * mm), _grafico(dados["serie"], kpi, titulo, largura)])
            )
    if "tabela_campanhas" in graficos or not executiva:
        story.append(Paragraph("Campanhas", est["h2"]))
        story.append(_campanhas(dados, kpis, moeda, largura, 10 if executiva else None, est))
    if cfg.get("comentarios"):
        story.append(Paragraph("Comentários", est["h2"]))
        for par in str(cfg["comentarios"]).split("\n\n"):
            story.append(Paragraph(escape(par).replace("\n", "<br/>"), est["p"]))
    doc.build(story, onFirstPage=_rodape, onLaterPages=_rodape)
    return buf.getvalue()
