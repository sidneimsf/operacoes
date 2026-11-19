"""
Relatorio do Retorno de documentos de um mes, por supervisor, em Excel e
PDF - pra imprimir e entregar/mandar a cada supervisor quem ja esta em dia
e o que ainda falta trazer. Recebe o dicionario do painel do mes
(main._montar_painel_retorno), o mesmo que a tela usa - ou o de todos os
meses (main._montar_painel_retorno_todos, painel["todos_meses"]): ai cada
linha e um mes de um colaborador e entra a coluna "Mes".
"""

import io
import os
import re
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SIGLAS = {"ok": "OK", "faltando": "F", "nao_se_aplica": "X"}


def _a_entregar(celula: dict, encerrada: bool) -> bool:
    """O supervisor ainda tem que trazer: veio faltando parte, ou nao veio (mes encerrado ou em andamento)."""
    if celula["situacao"] == "faltando":
        return True
    return celula["situacao"] is None and (celula["em_falta"] or not encerrada)


def _sigla(celula: dict | None) -> str:
    if celula is None:
        return ""  # documento que nao existe nesse mes (13o fora de nov/dez)
    return SIGLAS.get(celula["situacao"], "—")


def _rotulo_curto(label: str) -> str:
    """'Ponto 10/2026' -> 'Ponto'; 'Holerite 13º' fica igual."""
    return re.sub(r"\s+\d{2}/\d{4}$", "", label)


def montar_relatorio(painel: dict) -> list[dict]:
    """
    Um bloco por supervisor: quem esta em dia e quem tem algo a entregar,
    com a lista do que falta (e a observacao, quando tem).
    """
    documentos = painel["documentos"]
    todos = painel.get("todos_meses", False)
    blocos = []
    for grupo in painel["grupos"]:
        em_dia, a_entregar = [], []
        for linha in grupo["colaboradores"]:
            faltas = []
            encerrada = linha.get("encerrada", painel["encerrada"])
            for doc in documentos:
                celula = linha["celulas"].get(doc["chave"])
                if celula is None:
                    continue
                if _a_entregar(celula, encerrada):
                    texto = celula.get("label") or doc["label"]
                    if celula["situacao"] == "faltando":
                        texto += f" (faltando parte{': ' + celula['observacao'] if celula['observacao'] else ''})"
                    faltas.append(texto)
            outros = 0 if todos else linha["em_falta_total"] - linha["em_falta_mes"]
            item = {
                "nome": linha["nome"],
                "status": linha["status"],
                "competencia": linha.get("competencia"),
                "siglas": [_sigla(linha["celulas"].get(d["chave"])) for d in documentos],
                "faltas": faltas,
                "outros_meses": max(outros, 0),
            }
            (a_entregar if faltas else em_dia).append(item)
        blocos.append({
            "supervisor": grupo["supervisor_nome"],
            "em_dia": em_dia,
            "a_entregar": a_entregar,
            # todos os meses: conta pessoas, nao linhas (uma pessoa pode ter varios meses)
            "total": len({l["id"] for l in grupo["colaboradores"]}) if todos else len(em_dia) + len(a_entregar),
        })
    return blocos


def _situacao_texto(item: dict) -> str:
    if not item["faltas"]:
        texto = "Em dia"
    else:
        texto = "Falta: " + "; ".join(item["faltas"])
    if item["outros_meses"]:
        texto += f" · + {item['outros_meses']} doc. de outros meses"
    return texto


def _nome_com_status(item: dict) -> str:
    if item["status"] == "afastado":
        return f"{item['nome']} (afastado)"
    if item["status"] == "desligado":
        return f"{item['nome']} (desligado)"
    return item["nome"]


# ---------------------------------------------------------------------------
# Excel: aba Resumo + uma aba por supervisor
# ---------------------------------------------------------------------------

_FILL_CAB = PatternFill("solid", fgColor="17354F")
_FILL_OK = PatternFill("solid", fgColor="E3F1E8")
_FILL_FALTA = PatternFill("solid", fgColor="FBE4E1")
_FILL_SECAO = PatternFill("solid", fgColor="EEF1F7")
_BORDA = Border(bottom=Side(style="thin", color="D7DEEA"))


def _nome_aba(nome: str, usados: set) -> str:
    base = re.sub(r"[\\/*?:\[\]]", " ", nome).strip()[:28] or "Supervisor"
    nome_final, n = base, 2
    while nome_final.lower() in usados:
        nome_final = f"{base[:25]} {n}"
        n += 1
    usados.add(nome_final.lower())
    return nome_final


def _subtitulo_bloco(painel: dict, b: dict) -> str:
    if painel.get("todos_meses"):
        return f"{b['total']} colaboradores com documento em falta · {len(b['a_entregar']) + len(b['em_dia'])} meses em aberto"
    return f"{b['total']} colaboradores · {len(b['em_dia'])} em dia · {len(b['a_entregar'])} com documento a entregar"


def _titulo_competencia(painel: dict) -> str:
    """'Outubro/2026' ou 'Outubro/2026 · CORDSUL' quando filtrado por empresa."""
    if painel.get("empresa_nome"):
        return f"{painel['nome']} · {painel['empresa_nome']}"
    return painel["nome"]


def gerar_excel(painel: dict, gerado_em: str) -> bytes:
    documentos = painel["documentos"]
    todos = painel.get("todos_meses", False)
    blocos = montar_relatorio(painel)
    wb = Workbook()

    resumo = wb.active
    resumo.title = "Resumo"
    resumo.append([f"Retorno de documentos · {_titulo_competencia(painel)}"])
    resumo["A1"].font = Font(bold=True, size=14, color="17354F")
    resumo.append([f"Gerado em {gerado_em}" + ("" if painel["encerrada"] else " · mês ainda em andamento")])
    resumo["A2"].font = Font(italic=True, color="5B6B82")
    resumo.append([])
    if todos:
        resumo.append(["Supervisor", "Colaboradores com falta", "Meses em aberto"])
        for celula in resumo[4]:
            celula.font = Font(bold=True, color="FFFFFF")
            celula.fill = _FILL_CAB
        for b in blocos:
            resumo.append([b["supervisor"], b["total"], len(b["a_entregar"]) + len(b["em_dia"])])
        resumo.append([
            "Total", sum(b["total"] for b in blocos), sum(len(b["a_entregar"]) + len(b["em_dia"]) for b in blocos),
        ])
        for celula in resumo[resumo.max_row]:
            celula.font = Font(bold=True)
    else:
        _resumo_excel_do_mes(resumo, blocos)
    for i, largura in enumerate([34, 22, 16, 12, 10], start=1):
        resumo.column_dimensions[get_column_letter(i)].width = largura

    usados = {"resumo"}
    cabecalho = ["Funcionário"] + (["Mês"] if todos else []) + [d["label"] for d in documentos] + ["Situação"]
    primeira_sigla = 3 if todos else 2
    n_col = len(cabecalho)
    for b in blocos:
        ws = wb.create_sheet(_nome_aba(b["supervisor"], usados))
        ws.append([f"Retorno de documentos · {_titulo_competencia(painel)} · {b['supervisor']}"])
        ws["A1"].font = Font(bold=True, size=13, color="17354F")
        ws.append([_subtitulo_bloco(painel, b)])
        ws["A2"].font = Font(color="5B6B82")
        ws.append(["OK = entregue · F = faltando parte · X = não se aplica · — = não entregue"])
        ws["A3"].font = Font(italic=True, size=9, color="5B6B82")
        ws.append([])

        for titulo, itens, fill in (("A ENTREGAR", b["a_entregar"], _FILL_FALTA), ("EM DIA", b["em_dia"], _FILL_OK)):
            if not itens:
                continue
            ws.append([f"{titulo} ({len(itens)})"])
            linha_secao = ws.max_row
            ws.cell(row=linha_secao, column=1).font = Font(bold=True, color="17354F")
            for col in range(1, n_col + 1):
                ws.cell(row=linha_secao, column=col).fill = _FILL_SECAO
            ws.append(cabecalho)
            for celula in ws[ws.max_row]:
                celula.font = Font(bold=True, color="FFFFFF")
                celula.fill = _FILL_CAB
                celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            for item in itens:
                mes = [item["competencia"]] if todos else []
                ws.append([_nome_com_status(item)] + mes + item["siglas"] + [_situacao_texto(item)])
                r = ws.max_row
                for col in range(primeira_sigla, n_col):
                    ws.cell(row=r, column=col).alignment = Alignment(horizontal="center")
                situacao = ws.cell(row=r, column=n_col)
                situacao.fill = fill
                situacao.alignment = Alignment(wrap_text=True, vertical="top")
                for col in range(1, n_col + 1):
                    ws.cell(row=r, column=col).border = _BORDA
            ws.append([])

        ws.column_dimensions["A"].width = 38
        for col in range(2, n_col):
            ws.column_dimensions[get_column_letter(col)].width = 15
        ws.column_dimensions[get_column_letter(n_col)].width = 60
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _resumo_excel_do_mes(resumo, blocos: list[dict]) -> None:
    resumo.append(["Supervisor", "Colaboradores", "Em dia", "A entregar", "% em dia"])
    for celula in resumo[4]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = _FILL_CAB
    for b in blocos:
        pct = len(b["em_dia"]) / b["total"] if b["total"] else 0
        resumo.append([b["supervisor"], b["total"], len(b["em_dia"]), len(b["a_entregar"]), pct])
        resumo.cell(row=resumo.max_row, column=5).number_format = "0%"
    total = sum(b["total"] for b in blocos)
    em_dia = sum(len(b["em_dia"]) for b in blocos)
    resumo.append(["Total", total, em_dia, total - em_dia, em_dia / total if total else 0])
    for celula in resumo[resumo.max_row]:
        celula.font = Font(bold=True)
    resumo.cell(row=resumo.max_row, column=5).number_format = "0%"


# ---------------------------------------------------------------------------
# PDF: uma pagina (ou mais) por supervisor, pronta pra imprimir
# ---------------------------------------------------------------------------

AZUL = colors.HexColor("#17354f")
DOURADO = colors.HexColor("#7d5f11")
VERMELHO = colors.HexColor("#c13327")
VERDE = colors.HexColor("#1f6b41")
CINZA = colors.HexColor("#5b6b82")
BORDA = colors.HexColor("#d7deea")
FUNDO = colors.HexColor("#eef1f7")
FUNDO_VERMELHO = colors.HexColor("#fbe4e1")
FUNDO_VERDE = colors.HexColor("#e3f1e8")
CAMINHO_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "logo-starsul.png")

PAGINA = landscape(A4)
LARGURA_UTIL = PAGINA[0] - 3 * cm

ESTILOS = {
    "normal": ParagraphStyle("normal", fontName="Helvetica", fontSize=9, leading=12, textColor=AZUL),
    "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=AZUL),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=13, textColor=CINZA),
    "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=AZUL, spaceBefore=10, spaceAfter=5),
    "celula": ParagraphStyle("celula", fontName="Helvetica", fontSize=8.5, leading=10.5, textColor=AZUL),
    "celula_cab": ParagraphStyle("celula_cab", fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=CINZA, alignment=TA_CENTER),
    "celula_cab_esq": ParagraphStyle("celula_cab_esq", fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=CINZA),
    "sigla": ParagraphStyle("sigla", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=AZUL, alignment=TA_CENTER),
    "pequeno": ParagraphStyle("pequeno", fontName="Helvetica", fontSize=7.5, leading=10, textColor=CINZA),
}

COR_SIGLA = {"OK": "#1f6b41", "F": "#c13327", "X": "#5b6b82", "—": "#c13327"}


def _p(texto, estilo="normal") -> Paragraph:
    return Paragraph(escape(str(texto)) if texto is not None else "", ESTILOS[estilo])


def _tabela_colaboradores(itens: list[dict], documentos: list[dict], cor_fundo, mostrar_situacao: bool, com_mes: bool = False) -> Table:
    n_docs = len(documentos)
    largura_doc = 1.75 * cm
    largura_mes = 2.6 * cm if com_mes else 0
    largura_nome = 7 * cm if mostrar_situacao else LARGURA_UTIL - n_docs * largura_doc - 2.2 * cm - largura_mes
    larguras = [largura_nome] + ([largura_mes] if com_mes else []) + [largura_doc] * n_docs
    cabecalho = (
        [_p("Funcionário", "celula_cab_esq")]
        + ([_p("Mês", "celula_cab_esq")] if com_mes else [])
        + [_p(_rotulo_curto(d["label"]), "celula_cab") for d in documentos]
    )
    if mostrar_situacao:
        larguras.append(LARGURA_UTIL - sum(larguras))
        cabecalho.append(_p("O que falta trazer", "celula_cab_esq"))
    else:
        larguras.append(2.2 * cm)
        cabecalho.append(_p("Conferido", "celula_cab"))

    dados = [cabecalho]
    for item in itens:
        linha = [_p(_nome_com_status(item), "celula")]
        if com_mes:
            linha.append(_p(item["competencia"], "celula"))
        for sigla in item["siglas"]:
            if not sigla:
                linha.append(_p("", "sigla"))
                continue
            linha.append(Paragraph(f'<font color="{COR_SIGLA[sigla]}">{sigla}</font>', ESTILOS["sigla"]))
        if mostrar_situacao:
            texto = escape(" · ".join(item["faltas"]))
            if item["outros_meses"]:
                texto += f'<br/><font size="7" color="#5b6b82">+ {item["outros_meses"]} doc. de outros meses em falta</font>'
            linha.append(Paragraph(texto, ESTILOS["celula"]))
        else:
            texto = "Em dia"
            if item["outros_meses"]:
                texto += f'<br/><font size="7" color="#c13327">+{item["outros_meses"]} outros meses</font>'
            linha.append(Paragraph(f'<font color="#1f6b41">{texto}</font>', ESTILOS["sigla"]))
        dados.append(linha)

    tabela = Table(dados, colWidths=larguras, repeatRows=1)
    estilo = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDA),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (-1, 1), (-1, -1), cor_fundo),
    ]
    tabela.setStyle(TableStyle(estilo))
    return tabela


def gerar_pdf(painel: dict, gerado_em: str) -> bytes:
    documentos = painel["documentos"]
    todos = painel.get("todos_meses", False)
    blocos = montar_relatorio(painel)
    buffer = io.BytesIO()
    competencia = _titulo_competencia(painel)

    def moldura(canvas, doc):
        canvas.saveState()
        largura, altura = PAGINA
        if os.path.exists(CAMINHO_LOGO):
            canvas.drawImage(CAMINHO_LOGO, 1.5 * cm, altura - 2.1 * cm, width=3 * cm, height=1.35 * cm,
                             preserveAspectRatio=True, mask="auto")
        canvas.setFillColor(AZUL)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawRightString(largura - 1.5 * cm, altura - 1.35 * cm, "Retorno de documentos")
        canvas.setFont("Helvetica", 9.5)
        canvas.setFillColor(CINZA)
        canvas.drawRightString(
            largura - 1.5 * cm, altura - 1.85 * cm,
            f"{competencia} · só o que está em falta" if todos else f"Competência {competencia}",
        )
        canvas.setStrokeColor(DOURADO)
        canvas.setLineWidth(1.4)
        canvas.line(1.5 * cm, altura - 2.3 * cm, largura - 1.5 * cm, altura - 2.3 * cm)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.5 * cm, 1 * cm, f"Grupo Star Sul · Operações · gerado em {gerado_em}")
        canvas.drawRightString(largura - 1.5 * cm, 1 * cm, f"página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=PAGINA, title=f"Retorno de documentos {competencia}", author="Operações Grupo Star Sul",
        topMargin=2.7 * cm, bottomMargin=1.6 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    legenda = "OK = entregue · F = faltando parte · X = não se aplica · — = não entregue"
    if not painel["encerrada"]:
        legenda += " · mês ainda em andamento"

    elementos = []
    for i, b in enumerate(blocos):
        if i:
            elementos.append(PageBreak())
        elementos.append(_p(f"Supervisor: {b['supervisor']}", "titulo"))
        elementos.append(_p(_subtitulo_bloco(painel, b), "sub"))
        elementos.append(_p(legenda, "pequeno"))
        elementos.append(Spacer(1, 6))
        elementos.append(_p("Recebido por (supervisor): ______________________________    Data: ____/____/______", "normal"))
        elementos.append(Spacer(1, 2))
        if b["a_entregar"]:
            elementos.append(Paragraph(f'<font color="#c13327">A entregar ({len(b["a_entregar"])})</font>', ESTILOS["secao"]))
            elementos.append(_tabela_colaboradores(b["a_entregar"], documentos, FUNDO_VERMELHO, True, todos))
        if b["em_dia"]:
            elementos.append(Paragraph(f'<font color="#1f6b41">Em dia ({len(b["em_dia"])})</font>', ESTILOS["secao"]))
            elementos.append(_tabela_colaboradores(b["em_dia"], documentos, FUNDO_VERDE, False, todos))

    if not elementos:
        elementos.append(_p(
            "Nenhum documento em falta com esses filtros." if todos else "Nenhum colaborador nesse mês com esses filtros.",
            "normal",
        ))
    doc.build(elementos, onFirstPage=moldura, onLaterPages=moldura)
    return buffer.getvalue()
