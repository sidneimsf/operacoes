"""
Gera o PDF do "Resumo do dia" a partir do dicionario montado em
resumo_dia.montar_resumo_dia - o mesmo conteudo da aba do CRM, em formato
de relatorio pra imprimir, arquivar ou mandar por e-mail.
"""

import io
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from crm_saude import formatar_moeda

AZUL = colors.HexColor("#17354f")
DOURADO = colors.HexColor("#7d5f11")
VERMELHO = colors.HexColor("#c13327")
VERDE = colors.HexColor("#1f6b41")
AMARELO = colors.HexColor("#a8760a")
AZUL_INFO = colors.HexColor("#2f5b9e")
CINZA = colors.HexColor("#5b6b82")
BORDA = colors.HexColor("#d7deea")
FUNDO = colors.HexColor("#eef1f7")

COR_NIVEL = {"alerta": VERMELHO, "atencao": AMARELO, "positivo": VERDE, "info": AZUL_INFO}
COR_STATUS = {"critico": VERMELHO, "atencao": AMARELO, "tranquilo": VERDE}
COR_URGENCIA = {"alta": VERMELHO, "media": AMARELO, "baixa": AZUL_INFO}
COR_FAIXA = {"risco": VERMELHO, "atencao": AMARELO, "saudavel": VERDE}
CAMINHO_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "logo-starsul.png")

LARGURA_UTIL = A4[0] - 3 * cm

ESTILOS = {
    "normal": ParagraphStyle("normal", fontName="Helvetica", fontSize=9, leading=12.5, textColor=AZUL),
    "pequeno": ParagraphStyle("pequeno", fontName="Helvetica", fontSize=7.5, leading=10, textColor=CINZA),
    "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=AZUL, spaceBefore=12, spaceAfter=6, keepWithNext=1),
    "manchete": ParagraphStyle("manchete", fontName="Helvetica", fontSize=11, leading=15, textColor=AZUL),
    "kpi_valor": ParagraphStyle("kpi_valor", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=AZUL),
    "kpi_label": ParagraphStyle("kpi_label", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=CINZA),
    "celula": ParagraphStyle("celula", fontName="Helvetica", fontSize=8, leading=10.5, textColor=AZUL),
    "celula_cab": ParagraphStyle("celula_cab", fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=CINZA),
    "status": ParagraphStyle("status", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=colors.white, alignment=TA_CENTER),
}


def _p(texto, estilo="normal") -> Paragraph:
    return Paragraph(escape(str(texto)) if texto is not None else "", ESTILOS[estilo])


def _data_br(iso: str) -> str:
    ano, mes, dia = iso.split("-")
    return f"{dia}/{mes}/{ano}"


def _horas(horas: float) -> str:
    inteiras = int(horas)
    minutos = round((horas - inteiras) * 60)
    return f"{inteiras}h{minutos:02d}" if minutos else f"{inteiras}h"


def _tabela(cabecalho: list[str], linhas: list[list], larguras: list[float]) -> Table:
    dados = [[_p(c, "celula_cab") for c in cabecalho]]
    for linha in linhas:
        dados.append([c if isinstance(c, Paragraph) else _p(c, "celula") for c in linha])
    tabela = Table(dados, colWidths=larguras, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDA),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, FUNDO),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabela


def _blocos_com_barra(itens: list[tuple[colors.Color, list]]) -> Table:
    """Linhas com uma barrinha colorida a esquerda (usado em leituras e pendencias)."""
    dados = [["", conteudo] for _, conteudo in itens]
    tabela = Table(dados, colWidths=[0.18 * cm, LARGURA_UTIL - 0.18 * cm])
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, (cor, _) in enumerate(itens):
        estilo.append(("BACKGROUND", (0, i), (0, i), cor))
    tabela.setStyle(TableStyle(estilo))
    return tabela


def _comparacao(indicador: dict, moeda: bool = False) -> str:
    if "direcao" not in indicador:
        return ""
    media = formatar_moeda(indicador["media"]) if moeda else f"{indicador['media']:g}".replace(".", ",")
    seta = {"acima": "acima", "abaixo": "abaixo", "normal": "dentro"}[indicador["direcao"]]
    cor = {"acima": "#c13327", "abaixo": "#1f6b41", "normal": "#5b6b82"}[indicador["direcao"]]
    if indicador["direcao"] == "normal":
        return f'<font color="{cor}">dentro do normal (média {media})</font>'
    return f'<font color="{cor}">{seta} da média ({media})</font>'


def _kpi(valor: str, rotulo: str, detalhe: str = "") -> list:
    celula = [Paragraph(escape(valor), ESTILOS["kpi_valor"]), Paragraph(escape(rotulo), ESTILOS["kpi_label"])]
    if detalhe:
        celula.append(Paragraph(detalhe, ESTILOS["kpi_label"]))
    return celula


def gerar_resumo_dia_pdf(r: dict) -> bytes:
    buffer = io.BytesIO()
    titulo_data = f"{_data_br(r['data'])} ({r['dia_semana']})"

    def moldura(canvas, doc):
        canvas.saveState()
        largura, altura = A4
        if os.path.exists(CAMINHO_LOGO):
            canvas.drawImage(CAMINHO_LOGO, 1.5 * cm, altura - 2.25 * cm, width=3.2 * cm, height=1.5 * cm,
                             preserveAspectRatio=True, mask="auto")
        canvas.setFillColor(AZUL)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawRightString(largura - 1.5 * cm, altura - 1.45 * cm, "Resumo da operação")
        canvas.setFont("Helvetica", 9.5)
        canvas.setFillColor(CINZA)
        canvas.drawRightString(largura - 1.5 * cm, altura - 1.95 * cm, titulo_data)
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(1.4)
        canvas.line(1.5 * cm, altura - 2.45 * cm, largura - 1.5 * cm, altura - 2.45 * cm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(CINZA)
        canvas.drawString(1.5 * cm, 1 * cm, f"Grupo Star Sul · Operações · gerado em {r['gerado_em']}")
        canvas.drawRightString(largura - 1.5 * cm, 1 * cm, f"página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=f"Resumo da operação {titulo_data}", author="Operações Grupo Star Sul",
        topMargin=2.9 * cm, bottomMargin=1.6 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    elementos = []

    # status + manchete
    status = Table([[_p(r["status"]["label"], "status"), _p(r["manchete"], "manchete")]],
                   colWidths=[3.4 * cm, LARGURA_UTIL - 3.4 * cm])
    status.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), COR_STATUS[r["status"]["chave"]]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos += [status, Spacer(1, 10)]

    # indicadores
    ind = r["indicadores"]
    horas = ind["horas_falta"]["valor"]
    kpis = [
        _kpi(str(ind["chamados_abertos"]["valor"]), "chamados abertos", _comparacao(ind["chamados_abertos"])),
        _kpi(str(ind["chamados_finalizados"]["valor"]), "chamados finalizados",
             f'backlog: {ind["backlog"]["valor"]} ({ind["backlog"]["urgentes"]} urgentes)'),
        _kpi(str(ind["reclamacoes"]["valor"]), "reclamações", _comparacao(ind["reclamacoes"])),
        _kpi(str(ind["visitas"]["valor"]), "visitas de supervisão", _comparacao(ind["visitas"])),
        _kpi(str(ind["faltas"]["valor"]), "faltas", (f"+ {_horas(horas)} de falta parcial" if horas else _comparacao(ind["faltas"]))),
        _kpi(str(ind["atestados"]["valor"]), "atestados ativos", f'{ind["ferias"]["valor"]} em férias'),
        _kpi(formatar_moeda(ind["custo_total"]["valor"]), "custos do dia", _comparacao(ind["custo_total"], moeda=True)),
        _kpi(str(ind["turnos_vagos"]["valor"]), "turnos vagos hoje", f'amanhã: {ind["turnos_vagos"]["amanha"]}'),
    ]
    largura_kpi = LARGURA_UTIL / 4
    grade = Table([kpis[:4], kpis[4:]], colWidths=[largura_kpi] * 4)
    grade.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, BORDA),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(grade)

    # leitura do dia
    elementos.append(_p("Leitura do dia", "secao"))
    elementos.append(_blocos_com_barra([(COR_NIVEL[i["nivel"]], _p(i["texto"])) for i in r["insights"]]))

    # pontos de atencao por cliente
    if r["pontos_atencao"]:
        elementos.append(_p("Onde olhar: pontos de atenção por cliente", "secao"))
        linhas = []
        for p in r["pontos_atencao"]:
            cliente = Paragraph(
                f"<b>{escape(p['cliente_nome'])}</b><br/><font size='7' color='#5b6b82'>{escape(p['empresa_nome'])}"
                f"{' · ' + escape(p['supervisor_nome']) if p['supervisor_nome'] else ''}</font>", ESTILOS["celula"])
            ocorrencias = Paragraph("<br/>".join("• " + escape(i["texto"]) for i in p["itens"]), ESTILOS["celula"])
            if p["score"] is not None:
                cor = COR_FAIXA.get(p["faixa"], CINZA).hexval().replace("0x", "#")
                saude = Paragraph(f"<font color='{cor}'><b>{p['score']}</b></font><br/><font size='7' color='#5b6b82'>{escape(p['faixa_label'])}</font>", ESTILOS["celula"])
            else:
                saude = _p("—", "celula")
            linhas.append([cliente, ocorrencias, saude, _p(p["leitura"], "celula")])
        elementos.append(_tabela(["Cliente", "Ocorrências do dia", "Saúde", "Leitura"], linhas,
                                 [4.2 * cm, 6.4 * cm, 1.5 * cm, LARGURA_UTIL - 12.1 * cm]))

    # pendencias para amanha
    if r["pendencias_amanha"]:
        elementos.append(_p("Pendências para amanhã", "secao"))
        elementos.append(_blocos_com_barra([(COR_URGENCIA[p["urgencia"]], _p(p["texto"])) for p in r["pendencias_amanha"]]))

    # ausencias
    if r["ausencias"]:
        linhas = [[a["colaborador_nome"], a["cliente_nome"] or "—",
                   a["tipo"] + (f" ({_horas(a['horas'])})" if a["horas"] else ""),
                   Paragraph(f"<font color='#c13327'><b>sem cobertura registrada</b></font>", ESTILOS["celula"]) if a["sem_cobertura"] else (a["cobertura"] or "—"),
                   a["descricao"] or ""] for a in r["ausencias"]]
        elementos.append(KeepTogether([_p("Ausências", "secao"), _tabela(
            ["Colaborador", "Posto", "Tipo", "Cobertura", "Observação"], linhas,
            [4.2 * cm, 3.8 * cm, 2.6 * cm, 3.4 * cm, LARGURA_UTIL - 14 * cm])]))

    # custos
    custos = r["custos"]
    if custos["diarias_detalhe"] or custos["por_tipo"]:
        bloco = [_p("Custos do dia", "secao")]
        if custos["diarias_detalhe"]:
            linhas = [[d["cliente_nome"] or "—", d["motivo"], d["quem_cobriu"] or "—", formatar_moeda(d["valor"] or 0), d["lancado_por"]]
                      for d in custos["diarias_detalhe"]]
            bloco.append(_tabela(["Cliente", "Motivo da diária", "Quem cobriu", "Valor", "Lançado por"], linhas,
                                 [4.6 * cm, 3.2 * cm, 3.8 * cm, 2.4 * cm, LARGURA_UTIL - 14 * cm]))
        if custos["por_tipo"]:
            texto = " · ".join(f"{c['tipo']}: {formatar_moeda(c['valor'])}" for c in custos["por_tipo"])
            bloco += [Spacer(1, 4), _p(f"Outras despesas: {texto}")]
        bloco += [Spacer(1, 3), _p(f"Total aguardando reembolso (todos os dias): {formatar_moeda(custos['pendentes_reembolso'])}", "pequeno")]
        elementos.append(KeepTogether(bloco))

    # chamados abertos
    if r["chamados_abertos"]:
        linhas = [[c["hora"], c["cliente_nome"], c["tipo_label"] + (" · URGENTE" if c["prioridade"] != "normal" else ""),
                   c["descricao"][:160], c["aberto_por"]] for c in r["chamados_abertos"]]
        elementos.append(_p("Chamados abertos no dia", "secao"))
        elementos.append(_tabela(["Hora", "Cliente", "Tipo", "Descrição", "Aberto por"], linhas,
                                 [1.2 * cm, 3.8 * cm, 3.2 * cm, LARGURA_UTIL - 11.2 * cm, 3 * cm]))

    # supervisores
    if r["por_supervisor"]:
        linhas = [[s["nome"], s["visitas"], s["chamados_abertos"], s["chamados_finalizados"], s["diarias_lancadas"],
                   formatar_moeda(s["custos_lancados"]), s["clientes_com_ocorrencia"]] for s in r["por_supervisor"]]
        elementos.append(KeepTogether([_p("Atividade por supervisor", "secao"), _tabela(
            ["Supervisor", "Visitas", "Chamados abertos", "Finalizados", "Diárias", "Custos", "Clientes c/ ocorrência"], linhas,
            [4.4 * cm, 1.6 * cm, 2.4 * cm, 2 * cm, 1.6 * cm, 2.6 * cm, LARGURA_UTIL - 14.6 * cm])]))

    # linha do tempo
    if r["linha_do_tempo"]:
        linhas = [[t["hora"], Paragraph(f"<b>{escape(t['titulo'])}</b>", ESTILOS["celula"]), t["detalhe"] or ""]
                  for t in r["linha_do_tempo"][:80]]
        elementos.append(_p("Linha do tempo do dia", "secao"))
        elementos.append(_tabela(["Hora", "O que aconteceu", "Detalhe"], linhas,
                                 [1.2 * cm, 6.8 * cm, LARGURA_UTIL - 8 * cm]))
        if len(r["linha_do_tempo"]) > 80:
            elementos.append(_p(f"... e mais {len(r['linha_do_tempo']) - 80} registros (veja a aba Resumo do dia no CRM).", "pequeno"))

    doc.build(elementos, onFirstPage=moldura, onLaterPages=moldura)
    return buffer.getvalue()
