"""
PDF da movimentacao de cobranca do mes (menu Gerencia): uma secao por
empresa, com aliquotas, linhas por remessa e totais. Mesmos calculos da
tela e do Excel (movimentacao.calcular_linha).
"""

import io
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from movimentacao import TIPOS_SERVICO_POR_CHAVE, calcular_linha, formatar_moeda, nome_mes, observacao_completa, texto_composicao

AZUL = colors.HexColor("#17354f")
DOURADO = colors.HexColor("#7d5f11")
CINZA = colors.HexColor("#5b6b82")
VERMELHO = colors.HexColor("#c13327")
VERDE = colors.HexColor("#1f6b41")
BORDA = colors.HexColor("#d7deea")
FUNDO = colors.HexColor("#eef1f7")
CAMINHO_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "logo-starsul.png")

PAGINA = landscape(A4)
LARGURA_UTIL = PAGINA[0] - 2.4 * cm

ESTILOS = {
    "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=AZUL, spaceAfter=2),
    "pequeno": ParagraphStyle("pequeno", fontName="Helvetica", fontSize=8, leading=10.5, textColor=CINZA, spaceAfter=8),
    "celula": ParagraphStyle("celula", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=AZUL),
    "celula_num": ParagraphStyle("celula_num", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=AZUL, alignment=TA_RIGHT),
    "celula_obs": ParagraphStyle("celula_obs", fontName="Helvetica", fontSize=6.5, leading=8, textColor=CINZA),
    "celula_cab": ParagraphStyle("celula_cab", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=CINZA),
    "celula_cab_num": ParagraphStyle("celula_cab_num", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=CINZA, alignment=TA_RIGHT),
    "total": ParagraphStyle("total", fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=AZUL, alignment=TA_RIGHT),
    "total_txt": ParagraphStyle("total_txt", fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=AZUL),
}

CABECALHO = ["Rem.", "Cliente", "Serviço", "Valor nota", "ISS", "INSS", "Boleto", "Nº NF", "Venc.", "Nota", "Boleto", "Enviado", "Docs"]
LARGURAS = [1.0, 9.0, 2.0, 2.3, 1.8, 1.8, 2.3, 1.3, 1.2, 1.2, 1.3, 1.4, 1.2]


def _p(texto, estilo="celula") -> Paragraph:
    return Paragraph(escape(str(texto)) if texto not in (None, "") else "", ESTILOS[estilo])


def _status(ok: bool) -> Paragraph:
    cor = "#1f6b41" if ok else "#c13327"
    return Paragraph(f'<font color="{cor}"><b>{"OK" if ok else "pend."}</b></font>', ESTILOS["celula"])


def _cliente(linha) -> list:
    detalhes = " · ".join(p for p in [linha.cnpj, linha.municipio] if p)
    celula = [_p(linha.nome_cliente)]
    if detalhes:
        celula.append(_p(detalhes, "celula_obs"))
    for texto in (texto_composicao(linha.composicao), observacao_completa(linha)):
        if texto:
            celula.append(_p(texto, "celula_obs"))
    return celula


def _tabela_empresa(cab) -> Table:
    escala = LARGURA_UTIL / sum(LARGURAS)
    dados = [[_p(c, "celula_cab_num" if 3 <= i <= 6 else "celula_cab") for i, c in enumerate(CABECALHO)]]
    estilo = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDA),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, FUNDO),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    totais = {"valor_nota": 0.0, "valor_iss": 0.0, "valor_inss": 0.0, "valor_boleto": 0.0}
    for linha in sorted(cab.linhas, key=lambda l: (l.remessa, l.ordem, l.id)):
        calc = calcular_linha(linha, cab)
        for chave in totais:
            totais[chave] += calc[chave]
        tipo = TIPOS_SERVICO_POR_CHAVE.get(linha.tipo_servico)
        dados.append([
            _p(f"{linha.remessa}ª"),
            _cliente(linha),
            _p(tipo["label"].split(" (")[0] if tipo else linha.tipo_servico),
            _p(formatar_moeda(calc["valor_nota"]), "celula_num"),
            _p(formatar_moeda(calc["valor_iss"]) if linha.retem_iss else "—", "celula_num"),
            _p(formatar_moeda(calc["valor_inss"]) if linha.retem_inss else "—", "celula_num"),
            _p(formatar_moeda(calc["valor_boleto"]), "celula_num"),
            _p(linha.numero_nota),
            _p(linha.vencimento),
            _status(linha.nota_ok),
            _status(linha.boleto_ok),
            _status(linha.cliente_ok),
            _status(linha.documentos_ok) if linha.exige_documentos else _p("—"),
        ])
    dados.append([
        "", _p(f"TOTAL ({len(cab.linhas)} clientes)", "total_txt"), "",
        _p(formatar_moeda(totais["valor_nota"]), "total"),
        _p(formatar_moeda(totais["valor_iss"]), "total"),
        _p(formatar_moeda(totais["valor_inss"]), "total"),
        _p(formatar_moeda(totais["valor_boleto"]), "total"),
        "", "", "", "", "", "",
    ])
    estilo.append(("LINEABOVE", (0, -1), (-1, -1), 0.8, AZUL))
    tabela = Table(dados, colWidths=[l * escala for l in LARGURAS], repeatRows=1)
    tabela.setStyle(TableStyle(estilo))
    return tabela


def gerar_movimentacao_pdf(cabecalhos: list, ano: int, mes: int, gerado_em: str) -> bytes:
    buffer = io.BytesIO()
    titulo = f"Movimentação de cobrança · {nome_mes(mes).capitalize()}/{ano}"

    def moldura(canvas, doc):
        canvas.saveState()
        largura, altura = PAGINA
        if os.path.exists(CAMINHO_LOGO):
            canvas.drawImage(CAMINHO_LOGO, 1.2 * cm, altura - 2.0 * cm, width=2.8 * cm, height=1.3 * cm,
                             preserveAspectRatio=True, mask="auto")
        canvas.setFillColor(AZUL)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawRightString(largura - 1.2 * cm, altura - 1.35 * cm, titulo)
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(1.2)
        canvas.line(1.2 * cm, altura - 2.15 * cm, largura - 1.2 * cm, altura - 2.15 * cm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(CINZA)
        canvas.drawString(1.2 * cm, 0.8 * cm, f"Grupo Star Sul · Gerência · gerado em {gerado_em}")
        canvas.drawRightString(largura - 1.2 * cm, 0.8 * cm, f"página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=PAGINA, title=titulo, author="Operações Grupo Star Sul",
        topMargin=2.5 * cm, bottomMargin=1.3 * cm, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
    )
    elementos = []
    for i, cab in enumerate(cabecalhos):
        if i:
            elementos.append(PageBreak())
        aliquotas = [
            f"ISS {cab.aliquota_iss:g}%".replace(".", ","),
            f"INSS {cab.aliquota_inss:g}%".replace(".", ","),
        ]
        if cab.simples_limpeza is not None:
            aliquotas.append(f"Simples limpeza {cab.simples_limpeza:g}%".replace(".", ","))
        if cab.simples_apoio is not None:
            aliquotas.append(f"Simples apoio {cab.simples_apoio:g}%".replace(".", ","))
        elementos.append(_p(f"{cab.empresa.nome} — ref. serviços prestados em {nome_mes(mes)}/{ano}", "secao"))
        elementos.append(_p(" · ".join(aliquotas) + (" · mês fechado" if cab.fechado else ""), "pequeno"))
        if cab.linhas:
            elementos.append(_tabela_empresa(cab))
        else:
            elementos.append(_p("Nenhum cliente lançado.", "pequeno"))
        elementos.append(Spacer(1, 4))
    if not elementos:
        elementos.append(_p("Nenhuma movimentação lançada para este mês.", "pequeno"))

    doc.build(elementos, onFirstPage=moldura, onLaterPages=moldura)
    return buffer.getvalue()
