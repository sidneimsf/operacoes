"""
Gera a folha ponto (cartao ponto) de um colaborador em PDF, pra um mes
especifico. Formato simplificado: sem horario nem CTPS/Serie, conforme
pedido - so o essencial pra assinatura manual mensal.
"""

import calendar
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DIAS_SEMANA_ABREV = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]


def gerar_folha_ponto_pdf(colaborador, ano: int, mes: int) -> bytes:
    """Recebe um objeto Colaborador (com empresa e cliente carregados) e
    devolve os bytes do PDF do cartao ponto daquele mes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    estilo_normal = ParagraphStyle("normal9", parent=styles["Normal"], fontSize=9, leading=13)
    estilo_titulo = ParagraphStyle("titulo", parent=styles["Normal"], fontSize=11, leading=14, fontName="Helvetica-Bold")

    empresa = colaborador.empresa
    cliente = colaborador.cliente

    elementos = []
    elementos.append(Paragraph(f"<b>Empresa:</b> {empresa.razao_social or empresa.nome}", estilo_normal))
    elementos.append(Paragraph(f"<b>CNPJ:</b> {empresa.cnpj or '—'}", estilo_normal))
    if cliente is not None:
        elementos.append(Paragraph(f"<b>Cliente:</b> {cliente.nome}", estilo_normal))
        if cliente.cidade:
            elementos.append(Paragraph(f"<b>Cidade/UF:</b> {cliente.cidade} SC", estilo_normal))
    elementos.append(Spacer(1, 10))

    registro_nome = f"{colaborador.registro} - {colaborador.nome}" if colaborador.registro else colaborador.nome
    elementos.append(Paragraph(registro_nome.upper(), estilo_titulo))
    if colaborador.cargo:
        elementos.append(Paragraph(colaborador.cargo, estilo_normal))
    if colaborador.data_admissao:
        elementos.append(Paragraph(f"<b>Admissão:</b> {colaborador.data_admissao.strftime('%d/%m/%Y')}", estilo_normal))
    elementos.append(Spacer(1, 6))

    total_dias = calendar.monthrange(ano, mes)[1]
    periodo = f"01/{mes:02d}/{ano} a {total_dias:02d}/{mes:02d}/{ano}"
    elementos.append(Paragraph(f"<b>Cartão Ponto - {periodo}</b>", estilo_titulo))
    elementos.append(Spacer(1, 8))

    cabecalho1 = ["Dias", "Entrada", "Intervalo", "", "Saída", "Assinatura"]
    cabecalho2 = ["", "", "Saída", "Entrada", "", ""]
    linhas_tabela = [cabecalho1, cabecalho2]

    for dia in range(1, total_dias + 1):
        d = date(ano, mes, dia)
        abrev = DIAS_SEMANA_ABREV[d.weekday()]
        if abrev == "Dom":
            linhas_tabela.append([f"{dia:02d} {abrev}", "Dom", "Dom", "Dom", "Dom", "Dom"])
        else:
            linhas_tabela.append([f"{dia:02d} {abrev}", "", "", "", "", ""])

    largura_dias = 2.2 * cm
    largura_assinatura = 5 * cm
    largura_meio = (17.4 * cm - largura_dias - largura_assinatura) / 4

    tabela = Table(
        linhas_tabela,
        colWidths=[largura_dias] + [largura_meio] * 4 + [largura_assinatura],
        rowHeights=[0.55 * cm] * 2 + [0.5 * cm] * total_dias,
    )
    tabela.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
                ("SPAN", (0, 0), (0, 1)),
                ("SPAN", (1, 0), (1, 1)),
                ("SPAN", (2, 0), (3, 0)),
                ("SPAN", (4, 0), (4, 1)),
                ("SPAN", (5, 0), (5, 1)),
            ]
        )
    )
    elementos.append(tabela)

    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("____/____/____.  " + "_" * 45, estilo_normal))
    elementos.append(Paragraph("Assinatura do Diretor", estilo_normal))
    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph("Reconheço a exatidão destas anotações.", estilo_normal))

    doc.build(elementos)
    return buffer.getvalue()
