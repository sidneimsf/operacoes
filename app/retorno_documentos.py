"""
Retorno de documentos: todo mes o supervisor recolhe com cada colaborador
os documentos assinados (ponto, holerite, VA/VT, ficha de EPI e, em
novembro/dezembro, o holerite do 13o) e entrega no escritorio, que marca
o que voltou. Antes era a planilha "Retorno de documentos.xlsx", uma aba
por mes, um bloco por supervisor.

Competencia = o mes do ponto. Na competencia 10/2026 voltam o ponto e o
holerite de 10/2026 e o VA/VT e a ficha de EPI de 11/2026 (os beneficios
do mes seguinte, entregues junto).

Situacao de cada documento:
  ok            - entregue  ("OK" na planilha)
  nao_se_aplica - o colaborador nao tem esse documento neste mes ("X")
  faltando      - trouxe, mas falta parte (pagina, assinatura...) ("F")
  (sem registro)- pendente, ainda nao voltou (celula em branco)

"Em falta" (o alerta) = faltando em qualquer competencia, ou pendente
numa competencia ja encerrada (do mes passado pra tras), contando so a
partir de quando o colaborador entrou no acompanhamento (ver
inicio_acompanhamento).

Aqui ficam so as regras - as rotas estao em main.py.
"""

import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from io import BytesIO

from openpyxl import load_workbook

# primeira aba da planilha antiga - antes disso nao existe acompanhamento
INICIO_ACOMPANHAMENTO = (2025, 11)

SITUACOES = [
    {"chave": "ok", "label": "Entregue", "sigla": "OK"},
    {"chave": "faltando", "label": "Faltando parte", "sigla": "F"},
    {"chave": "nao_se_aplica", "label": "Não se aplica", "sigla": "X"},
]
CHAVES_SITUACAO = {s["chave"] for s in SITUACOES}

MESES_ABREV = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
MESES_NOME = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def somar_meses(ano: int, mes: int, quantidade: int) -> tuple[int, int]:
    indice = ano * 12 + (mes - 1) + quantidade
    return indice // 12, indice % 12 + 1


def competencia_de(dia: date) -> tuple[int, int]:
    return dia.year, dia.month


def ultima_competencia_encerrada(hoje: date) -> tuple[int, int]:
    """O mes passado: os documentos dele estao sendo recolhidos agora."""
    return somar_meses(hoje.year, hoje.month, -1)


def nome_competencia(ano: int, mes: int) -> str:
    return f"{MESES_NOME[mes - 1]}/{ano}"


def documentos_da_competencia(ano: int, mes: int) -> list[dict]:
    """Os documentos que voltam numa competencia, na ordem das colunas da planilha."""
    ano_seg, mes_seg = somar_meses(ano, mes, 1)
    atual = f"{mes:02d}/{ano}"
    seguinte = f"{mes_seg:02d}/{ano_seg}"
    documentos = [
        {"chave": "ponto", "label": f"Ponto {atual}"},
        {"chave": "holerite", "label": f"Holerite {atual}"},
    ]
    if mes in (11, 12):
        documentos.append({"chave": "holerite_13", "label": "Holerite 13º"})
    documentos += [
        {"chave": "va_vt", "label": f"VA/VT {seguinte}"},
        {"chave": "ficha_epi", "label": f"Ficha EPI {seguinte}"},
    ]
    return documentos


# colunas do painel "todos os meses" (cada linha e um mes; o 13o so existe em nov/dez)
DOCUMENTOS_TODOS_MESES = [
    {"chave": "ponto", "label": "Ponto"},
    {"chave": "holerite", "label": "Holerite"},
    {"chave": "holerite_13", "label": "Holerite 13º"},
    {"chave": "va_vt", "label": "VA/VT"},
    {"chave": "ficha_epi", "label": "Ficha EPI"},
]


def chaves_documentos(ano: int, mes: int) -> list[str]:
    return [d["chave"] for d in documentos_da_competencia(ano, mes)]


def competencias_entre(inicio: tuple[int, int], fim: tuple[int, int]) -> list[tuple[int, int]]:
    lista = []
    atual = inicio
    while atual <= fim:
        lista.append(atual)
        atual = somar_meses(atual[0], atual[1], 1)
    return lista


def colaborador_no_mes(colaborador, ano: int, mes: int) -> bool:
    """Trabalhou nesse mes: admitido ate o fim dele e nao desligado antes do inicio."""
    if colaborador.eh_posto_vago:
        return False
    primeiro_dia = date(ano, mes, 1)
    ano_seg, mes_seg = somar_meses(ano, mes, 1)
    if colaborador.data_admissao and colaborador.data_admissao >= date(ano_seg, mes_seg, 1):
        return False
    if colaborador.status == "desligado":
        if colaborador.data_desligamento is None or colaborador.data_desligamento < primeiro_dia:
            return False
    return True


def inicio_acompanhamento(colaborador, primeiro_registro: tuple[int, int] | None, hoje: date) -> tuple[int, int]:
    """
    A partir de qual competencia um mes em branco conta como pendencia.
    Nunca antes de INICIO_ACOMPANHAMENTO nem antes da admissao. Quem ja
    tem alguma marcacao comeca na primeira delas (quem nao estava na
    planilha antiga nao ganha meses e meses de pendencia de uma vez); quem
    nao tem nenhuma comeca na competencia que esta sendo recolhida agora.
    """
    inicio = INICIO_ACOMPANHAMENTO
    if colaborador.data_admissao:
        inicio = max(inicio, competencia_de(colaborador.data_admissao))
    referencia = ultima_competencia_encerrada(hoje)
    if primeiro_registro is not None:
        referencia = min(referencia, primeiro_registro)
    return max(inicio, referencia)


def montar_meses_do_colaborador(colaborador, registros: list, hoje: date) -> list[dict]:
    """
    Uma entrada por competencia do acompanhamento (mais recente primeiro),
    com a situacao de cada documento. registros = RetornoDocumento do
    colaborador. Vai ate a competencia sendo recolhida agora (o mes
    passado), ou alem se algo ja foi marcado adiantado no painel.
    """
    por_celula = {(r.ano, r.mes, r.documento): r for r in registros}
    primeiro = min(((r.ano, r.mes) for r in registros), default=None)
    inicio = inicio_acompanhamento(colaborador, primeiro, hoje)
    encerrada = ultima_competencia_encerrada(hoje)
    fim = max(encerrada, max(((r.ano, r.mes) for r in registros), default=encerrada))

    meses = []
    for ano, mes in competencias_entre(min(inicio, primeiro or inicio), fim):
        tem_registro = any((ano, mes, chave) in por_celula for chave in chaves_documentos(ano, mes))
        if not tem_registro and not colaborador_no_mes(colaborador, ano, mes):
            continue
        conta_pendente = inicio <= (ano, mes) <= encerrada
        documentos = []
        em_falta = 0
        for doc in documentos_da_competencia(ano, mes):
            registro = por_celula.get((ano, mes, doc["chave"]))
            situacao = registro.situacao if registro else None
            falta = situacao == "faltando" or (situacao is None and conta_pendente)
            em_falta += 1 if falta else 0
            documentos.append(
                {
                    **doc,
                    "situacao": situacao,
                    "observacao": registro.observacao if registro else None,
                    "em_falta": falta,
                    "atualizado_por": registro.atualizado_por.nome if registro and registro.atualizado_por else None,
                    "atualizado_em": registro.atualizado_em.isoformat() if registro and registro.atualizado_em else None,
                }
            )
        meses.append(
            {
                "ano": ano,
                "mes": mes,
                "nome": nome_competencia(ano, mes),
                "encerrada": (ano, mes) <= encerrada,
                "documentos": documentos,
                "em_falta": em_falta,
            }
        )
    meses.reverse()
    return meses


def contar_em_falta(colaborador, registros: list, hoje: date) -> int:
    return sum(m["em_falta"] for m in montar_meses_do_colaborador(colaborador, registros, hoje))


# ---------------------------------------------------------------------------
# Importacao da planilha antiga
# ---------------------------------------------------------------------------

def normalizar(texto) -> str:
    """Maiusculo, sem acento e sem pontuacao: 'Angélica  da Trindade ' -> 'ANGELICA DA TRINDADE'."""
    texto = unicodedata.normalize("NFD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", " ", texto.upper()).strip()


def _competencia_da_aba(titulo: str) -> tuple[int, int] | None:
    """'Nov2025' -> (2025, 11)."""
    achou = re.fullmatch(r"([A-Z]{3})\s*(\d{4})", normalizar(titulo).replace(" ", ""))
    if not achou or achou.group(1) not in MESES_ABREV:
        return None
    return int(achou.group(2)), MESES_ABREV.index(achou.group(1)) + 1


def _documento_da_coluna(cabecalho) -> str | None:
    texto = normalizar(cabecalho)
    if texto.startswith("PONTO"):
        return "ponto"
    if texto.startswith("HOLERITE 13"):
        return "holerite_13"
    if texto.startswith("HOLERITE"):
        return "holerite"
    if texto.startswith("VA VT") or texto.startswith("VT"):
        return "va_vt"
    if texto.startswith("FICHA"):
        return "ficha_epi"
    return None


def interpretar_celula(valor) -> tuple[str, str | None] | None:
    """
    Valor da planilha -> (situacao, observacao). None = em branco
    (pendente, nada a gravar). Texto livre que nao e OK/X/F vira
    observacao: 'férias' nao se aplica, 'refeita' entregue, o resto
    ('não assinou', 'rasurado') faltando parte.
    """
    if valor is None or not str(valor).strip():
        return None
    original = re.sub(r"\s+", " ", str(valor)).strip()
    texto = normalizar(original)
    if texto in ("OK", "0K"):
        return "ok", None
    if texto == "X":
        return "nao_se_aplica", None
    if texto == "F":
        return "faltando", None
    if texto.startswith("FERIAS"):
        return "nao_se_aplica", "Férias"
    if texto.startswith("REFEIT"):
        return "ok", original
    return "faltando", original


def ler_planilha(conteudo: bytes) -> list[dict]:
    """
    Uma linha por (aba, colaborador) da planilha antiga: competencia, nome
    como esta na planilha e as celulas preenchidas {documento: (situacao, obs)}.
    Cada aba tem blocos lado a lado (um por supervisor); cada linha de
    cabecalho com "Funcionário" define as colunas dos blocos abaixo dela.
    """
    livro = load_workbook(BytesIO(conteudo), read_only=True, data_only=True)
    linhas = []
    for aba in livro.worksheets:
        competencia = _competencia_da_aba(aba.title)
        if competencia is None:
            continue
        blocos: list[tuple[int, dict[int, str]]] = []  # (coluna do nome, {coluna: documento})
        for numero, valores in enumerate(aba.iter_rows(values_only=True), start=1):
            valores = list(valores)
            inicio_blocos = [i for i, v in enumerate(valores) if normalizar(v) == "FUNCIONARIO"]
            if inicio_blocos:
                blocos = []
                for i in inicio_blocos:
                    colunas = {}
                    for j in range(i + 1, len(valores)):
                        documento = _documento_da_coluna(valores[j])
                        if documento is None:
                            break
                        colunas[j] = documento
                    blocos.append((i, colunas))
                continue
            for coluna_nome, colunas in blocos:
                nome = valores[coluna_nome] if coluna_nome < len(valores) else None
                nome_limpo = re.sub(r"\s+", " ", str(nome or "")).strip()
                if not nome_limpo or normalizar(nome_limpo).startswith("OBS"):
                    continue
                if all(valores[j] is None for j in colunas if j < len(valores)) and len(nome_limpo.split()) == 1:
                    continue  # linha de titulo do bloco (nome do supervisor, ADMINISTRATIVO)
                celulas = {}
                for j, documento in colunas.items():
                    interpretado = interpretar_celula(valores[j] if j < len(valores) else None)
                    if interpretado is not None:
                        celulas[documento] = interpretado
                linhas.append(
                    {
                        "aba": aba.title,
                        "linha": numero,
                        "ano": competencia[0],
                        "mes": competencia[1],
                        "nome": nome_limpo,
                        "celulas": celulas,
                    }
                )
    return linhas


def casar_nomes(nomes: list[str], colaboradores: list) -> tuple[dict[str, object], list[dict]]:
    """
    Casa cada nome da planilha (normalizado) com um colaborador cadastrado,
    pelo nome exato sem acento/pontuacao/espacos. Homonimos: fica com o
    unico ativo, se houver um so; senao nao casa (vai pra conferencia).
    Devolve ({nome_normalizado: colaborador}, [nao casados com motivo]).
    """
    por_nome: dict[str, list] = {}
    for c in colaboradores:
        if not c.eh_posto_vago:
            por_nome.setdefault(normalizar(c.nome), []).append(c)

    casados = {}
    nao_casados = []
    for nome in sorted(set(nomes)):
        chave = normalizar(nome)
        candidatos = por_nome.get(chave, [])
        if len(candidatos) > 1:
            ativos = [c for c in candidatos if c.status != "desligado"]
            candidatos = ativos if len(ativos) == 1 else candidatos
        if len(candidatos) == 1:
            casados[chave] = candidatos[0]
        elif not candidatos:
            nao_casados.append({"nome": nome, "motivo": "Nenhum colaborador cadastrado com esse nome"})
        else:
            nao_casados.append({"nome": nome, "motivo": f"{len(candidatos)} colaboradores com esse mesmo nome"})
    return casados, nao_casados


SEMELHANCA_SUGESTAO = 0.75


def sugerir_colaborador(nome: str, colaboradores: list):
    """
    Pra um nome que nao casou: o colaborador de nome mais parecido, se for
    parecido o bastante. 'BEATRIZ ANDRADE' sugere 'BEATRIZ DE ANDRADE
    SILVA' (todas as palavras da planilha estao no cadastro). Devolve
    (colaborador, semelhanca) ou (None, 0). Quem decide e o escritorio.
    """
    chave = normalizar(nome)
    palavras = set(chave.split())
    melhor, nota_melhor = None, 0.0
    for c in colaboradores:
        if c.eh_posto_vago:
            continue
        outro = normalizar(c.nome)
        nota = SequenceMatcher(None, chave, outro).ratio()
        if len(palavras) >= 2 and palavras <= set(outro.split()):
            nota = max(nota, 0.9)
        if nota > nota_melhor:
            melhor, nota_melhor = c, nota
    if nota_melhor < SEMELHANCA_SUGESTAO:
        return None, 0.0
    return melhor, round(nota_melhor, 2)
