"""
Motor de analise do CRM: calcula a "saude" de cada cliente da carteira
(nota de 0 a 100) a partir dos sinais que o sistema ja registra no dia a
dia - reclamacoes, chamados parados, visitas de supervisao, postos vagos,
troca de colaboradores, faltas cobertas com diaria e pesquisas de
satisfacao - e resume a carteira inteira em indicadores, alertas de
contrato, prioridades e frases de leitura rapida (insights).

Fica fora do main.py porque e usado tanto pelas rotas do CRM quanto pelo
alerta semanal por e-mail (alertas_crm.py), que roda em background.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    Chamado,
    Cliente,
    ClienteContato,
    ClienteContrato,
    Colaborador,
    CustoDiario,
    HistoricoMapaServico,
    HorarioServico,
    PesquisaSatisfacao,
    VisitaSupervisao,
)

NOME_CLIENTE_INTERNO = "ESCRITÓRIO ADM"  # cliente ficticio usado pra chamados internos

JANELA_DIAS = 90  # periodo analisado para reclamacoes, trocas e faltas
JANELA_TENDENCIA_DIAS = 45  # compara os ultimos 45 dias com os 45 anteriores
JANELA_PESQUISA_DIAS = 365  # pesquisa mais antiga que isso nao conta
PESQUISA_DESATUALIZADA_DIAS = 180
DIAS_CHAMADO_PARADO = 7

STATUS_DIARIA_FALTA = {"falta", "atestado", "posto_vago"}

FAIXAS_SAUDE = [
    {"chave": "saudavel", "label": "Saudável", "minimo": 75},
    {"chave": "atencao", "label": "Atenção", "minimo": 50},
    {"chave": "risco", "label": "Em risco", "minimo": 0},
]

CATEGORIAS_MOTIVO = {
    "reclamacao": {"label": "Reclamações", "acao": "Ligar para o responsável e agendar uma conversa sobre as reclamações"},
    "visita": {"label": "Visitas atrasadas", "acao": "Agendar visita de supervisão esta semana"},
    "posto_vago": {"label": "Postos vagos", "acao": "Priorizar a cobertura dos postos vagos"},
    "satisfacao": {"label": "Satisfação baixa", "acao": "Dar retorno ao cliente sobre a última avaliação"},
    "rotatividade": {"label": "Troca de colaboradores", "acao": "Revisar a alocação: o posto está trocando muito de colaborador"},
    "chamado_parado": {"label": "Chamados parados", "acao": "Cobrar a finalização dos chamados em aberto"},
    "faltas": {"label": "Faltas recorrentes", "acao": "Investigar as faltas recorrentes no posto"},
    "quadro": {"label": "Quadro incompleto", "acao": "Completar o quadro de postos contratado"},
}

PAPEIS_CONTATO = [
    {"chave": "sindico", "label": "Síndico(a)"},
    {"chave": "subsindico", "label": "Subsíndico(a)"},
    {"chave": "administradora", "label": "Administradora"},
    {"chave": "zelador", "label": "Zelador(a)"},
    {"chave": "gerente", "label": "Gerente / Gestor"},
    {"chave": "financeiro", "label": "Financeiro"},
    {"chave": "outro", "label": "Outro"},
]
CHAVES_PAPEL_CONTATO = {p["chave"] for p in PAPEIS_CONTATO}

INDICES_REAJUSTE = [
    {"chave": "ipca", "label": "IPCA"},
    {"chave": "igpm", "label": "IGP-M"},
    {"chave": "inpc", "label": "INPC"},
    {"chave": "convencao", "label": "Convenção coletiva"},
    {"chave": "outro", "label": "Outro"},
]
CHAVES_INDICE_REAJUSTE = {i["chave"] for i in INDICES_REAJUSTE}


def faixa_da_nota(score: int) -> dict:
    for faixa in FAIXAS_SAUDE:
        if score >= faixa["minimo"]:
            return faixa
    return FAIXAS_SAUDE[-1]


def classificar_nps(nota: int) -> str:
    if nota >= 9:
        return "promotor"
    if nota >= 7:
        return "neutro"
    return "detrator"


def calcular_nps(notas: list[int]) -> int | None:
    """NPS classico: % promotores (9-10) menos % detratores (0-6), de -100 a +100."""
    if not notas:
        return None
    promotores = sum(1 for n in notas if n >= 9)
    detratores = sum(1 for n in notas if n <= 6)
    return round((promotores - detratores) * 100 / len(notas))


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def formatar_moeda(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _inicio_do_dia_utc(dia: date) -> datetime:
    return datetime.combine(dia, time.min, tzinfo=timezone.utc)


def alertas_do_contrato(contrato: ClienteContrato | None, hoje: date) -> list[dict]:
    """Vencimento e reajuste: o que precisa de acao comercial nos proximos meses."""
    if contrato is None:
        return []
    alertas = []

    if contrato.data_fim:
        dias = (contrato.data_fim - hoje).days
        if contrato.renovacao_automatica:
            if dias < 0:
                alertas.append({"tipo": "vigencia", "urgencia": "baixa", "dias": dias,
                                "texto": f"Renovou automaticamente há {-dias} dias — atualize a nova vigência"})
            elif dias <= 60:
                alertas.append({"tipo": "vigencia", "urgencia": "media", "dias": dias,
                                "texto": f"Renova automaticamente em {dias} dias — bom momento para negociar reajuste"})
        elif dias < 0:
            alertas.append({"tipo": "vigencia", "urgencia": "alta", "dias": dias,
                            "texto": f"Contrato vencido há {-dias} dias"})
        elif dias <= 30:
            alertas.append({"tipo": "vigencia", "urgencia": "alta", "dias": dias,
                            "texto": f"Contrato vence em {dias} dias"})
        elif dias <= 90:
            alertas.append({"tipo": "vigencia", "urgencia": "media", "dias": dias,
                            "texto": f"Contrato vence em {dias} dias"})

    if contrato.data_reajuste:
        dias = (contrato.data_reajuste - hoje).days
        if dias < 0:
            alertas.append({"tipo": "reajuste", "urgencia": "alta", "dias": dias,
                            "texto": f"Reajuste atrasado há {-dias} dias"})
        elif dias <= 30:
            alertas.append({"tipo": "reajuste", "urgencia": "alta", "dias": dias,
                            "texto": f"Reajuste previsto em {dias} dias"})
        elif dias <= 60:
            alertas.append({"tipo": "reajuste", "urgencia": "media", "dias": dias,
                            "texto": f"Reajuste previsto em {dias} dias"})

    return alertas


def serializar_contrato(c: ClienteContrato | None) -> dict | None:
    if c is None:
        return None
    indice = next((i for i in INDICES_REAJUSTE if i["chave"] == c.indice_reajuste), None)
    return {
        "id": c.id,
        "cliente_id": c.cliente_id,
        "valor_mensal": c.valor_mensal,
        "data_inicio": c.data_inicio.isoformat() if c.data_inicio else None,
        "data_fim": c.data_fim.isoformat() if c.data_fim else None,
        "renovacao_automatica": c.renovacao_automatica,
        "data_reajuste": c.data_reajuste.isoformat() if c.data_reajuste else None,
        "indice_reajuste": c.indice_reajuste,
        "indice_reajuste_label": indice["label"] if indice else None,
        "postos_contratados": c.postos_contratados,
        "observacoes": c.observacoes,
        "atualizado_em": c.atualizado_em.isoformat() if c.atualizado_em else None,
        "atualizado_por_nome": c.atualizado_por.nome if c.atualizado_por else None,
    }


def _pontuar(sinais: dict) -> list[dict]:
    """
    Transforma os sinais de um cliente em motivos que descontam pontos da
    nota (que comeca em 100). Cada motivo tem um teto, pra que um unico
    problema nao zere a nota sozinho.
    """
    motivos = []

    def adicionar(categoria: str, impacto: int, texto: str):
        if impacto > 0:
            motivos.append({"categoria": categoria, "impacto": impacto, "texto": texto})

    n = sinais["reclamacoes"]
    adicionar("reclamacao", min(n * 10, 30), f"{_plural(n, 'reclamação', 'reclamações')} nos últimos {JANELA_DIAS} dias")

    dias_sem_visita = sinais["dias_sem_visita"]
    if dias_sem_visita is None:
        adicionar("visita", 20, "Nenhuma visita de supervisão registrada")
    elif dias_sem_visita > 60:
        adicionar("visita", 20, f"{dias_sem_visita} dias sem visita de supervisão")
    elif dias_sem_visita > 30:
        adicionar("visita", 10, f"{dias_sem_visita} dias sem visita de supervisão")

    n = sinais["turnos_vagos"]
    adicionar("posto_vago", min(n * 8, 20), f"{_plural(n, 'turno vago', 'turnos vagos')} na escala semanal")

    nota = sinais["ultima_nota"]
    if nota is not None:
        if nota <= 6:
            adicionar("satisfacao", 20, f"Última avaliação foi {nota}/10 (detrator)")
        elif nota <= 8:
            adicionar("satisfacao", 5, f"Última avaliação foi {nota}/10 (neutro)")

    n = sinais["trocas_colaborador"]
    impacto = 15 if n >= 5 else 10 if n >= 3 else 5 if n >= 2 else 0
    adicionar("rotatividade", impacto, f"{_plural(n, 'colaborador saiu', 'colaboradores saíram')} do posto em {JANELA_DIAS} dias")

    n = sinais["chamados_parados"]
    adicionar("chamado_parado", min(n * 5, 15), f"{_plural(n, 'chamado aberto', 'chamados abertos')} há mais de {DIAS_CHAMADO_PARADO} dias")

    n = sinais["faltas"]
    impacto = 10 if n >= 6 else 5 if n >= 3 else 0
    adicionar("faltas", impacto, f"{_plural(n, 'falta coberta', 'faltas cobertas')} com diária em {JANELA_DIAS} dias")

    # so compara com o contratado quando o cliente ja tem escala no mapa de servico -
    # sem escala nenhuma, o mapa so nao foi preenchido ainda, nao da pra concluir falta de gente
    contratados = sinais["postos_contratados"]
    tem_escala = sinais["colaboradores_efetivos"] + sinais["turnos_vagos"] > 0
    if contratados and tem_escala:
        deficit = contratados - sinais["colaboradores_efetivos"]
        adicionar("quadro", min(deficit * 5, 15),
                  f"{sinais['colaboradores_efetivos']} de {contratados} postos contratados preenchidos")

    motivos.sort(key=lambda m: -m["impacto"])
    return motivos


def calcular_saude_carteira(db: Session, cliente_ids: list[int] | None = None) -> list[dict]:
    """
    Calcula a saude de todos os clientes ativos (ou so dos ids passados),
    com consultas agregadas - uma por fonte de dados, nao uma por cliente.
    """
    hoje = date.today()
    agora = datetime.now(timezone.utc)
    inicio_janela = hoje - timedelta(days=JANELA_DIAS)
    corte_tendencia = hoje - timedelta(days=JANELA_TENDENCIA_DIAS)

    query_clientes = db.query(Cliente).filter(Cliente.ativo.is_(True), Cliente.nome != NOME_CLIENTE_INTERNO)
    if cliente_ids is not None:
        query_clientes = query_clientes.filter(Cliente.id.in_(cliente_ids))
    clientes = query_clientes.order_by(Cliente.nome).all()
    ids = [c.id for c in clientes]
    if not ids:
        return []

    # eventos negativos (reclamacao, falta, saida de colaborador) por cliente e data - base da nota e da tendencia
    reclamacoes: dict[int, list[date]] = {}
    for cliente_id, criado_em in (
        db.query(Chamado.cliente_id, Chamado.criado_em)
        .filter(Chamado.cliente_id.in_(ids), Chamado.tipo == "reclamacao", Chamado.criado_em >= _inicio_do_dia_utc(inicio_janela))
        .all()
    ):
        reclamacoes.setdefault(cliente_id, []).append(criado_em.date())

    chamados_parados = dict(
        db.query(Chamado.cliente_id, func.count(Chamado.id))
        .filter(Chamado.cliente_id.in_(ids), Chamado.status != "finalizado",
                Chamado.criado_em < agora - timedelta(days=DIAS_CHAMADO_PARADO))
        .group_by(Chamado.cliente_id)
        .all()
    )

    ultimas_visitas = dict(
        db.query(VisitaSupervisao.cliente_id, func.max(VisitaSupervisao.data_visita))
        .filter(VisitaSupervisao.cliente_id.in_(ids))
        .group_by(VisitaSupervisao.cliente_id)
        .all()
    )

    posto_vago = db.query(Colaborador).filter_by(eh_posto_vago=True).first()
    posto_vago_id = posto_vago.id if posto_vago else -1

    turnos_vagos = dict(
        db.query(HorarioServico.cliente_id, func.count(HorarioServico.id))
        .filter(HorarioServico.cliente_id.in_(ids), HorarioServico.colaborador_id == posto_vago_id,
                HorarioServico.data_fim.is_(None))
        .group_by(HorarioServico.cliente_id)
        .all()
    )

    colaboradores_efetivos = dict(
        db.query(HorarioServico.cliente_id, func.count(func.distinct(HorarioServico.colaborador_id)))
        .filter(HorarioServico.cliente_id.in_(ids), HorarioServico.colaborador_id != posto_vago_id,
                HorarioServico.data_fim.is_(None))
        .group_by(HorarioServico.cliente_id)
        .all()
    )

    # o log grava um evento por dia/turno; conta cada colaborador uma vez por cliente
    saidas: dict[int, dict[int, date]] = {}
    for cliente_id, colaborador_id, criado_em in (
        db.query(HistoricoMapaServico.cliente_id, HistoricoMapaServico.colaborador_id, HistoricoMapaServico.criado_em)
        .filter(HistoricoMapaServico.cliente_id.in_(ids), HistoricoMapaServico.tipo_evento == "encerrado",
                HistoricoMapaServico.colaborador_id != posto_vago_id,
                HistoricoMapaServico.criado_em >= _inicio_do_dia_utc(inicio_janela))
        .all()
    ):
        por_colaborador = saidas.setdefault(cliente_id, {})
        dia = criado_em.date()
        if colaborador_id not in por_colaborador or dia > por_colaborador[colaborador_id]:
            por_colaborador[colaborador_id] = dia

    faltas: dict[int, list[date]] = {}
    custo_diarias: dict[int, float] = {}
    for cliente_id, dia, valor, status_diaria in (
        db.query(CustoDiario.cliente_id, CustoDiario.data, CustoDiario.valor, CustoDiario.status_diaria)
        .filter(CustoDiario.cliente_id.in_(ids), CustoDiario.status_diaria.is_not(None), CustoDiario.data >= inicio_janela)
        .all()
    ):
        custo_diarias[cliente_id] = custo_diarias.get(cliente_id, 0.0) + (valor or 0.0)
        if status_diaria in STATUS_DIARIA_FALTA:
            faltas.setdefault(cliente_id, []).append(dia)

    ultima_pesquisa: dict[int, PesquisaSatisfacao] = {}
    for p in (
        db.query(PesquisaSatisfacao)
        .filter(PesquisaSatisfacao.cliente_id.in_(ids),
                PesquisaSatisfacao.data_pesquisa >= hoje - timedelta(days=JANELA_PESQUISA_DIAS))
        .order_by(PesquisaSatisfacao.data_pesquisa.desc(), PesquisaSatisfacao.id.desc())
        .all()
    ):
        ultima_pesquisa.setdefault(p.cliente_id, p)

    contratos = {c.cliente_id: c for c in db.query(ClienteContrato).filter(ClienteContrato.cliente_id.in_(ids)).all()}

    total_contatos = dict(
        db.query(ClienteContato.cliente_id, func.count(ClienteContato.id))
        .filter(ClienteContato.cliente_id.in_(ids))
        .group_by(ClienteContato.cliente_id)
        .all()
    )

    linhas = []
    for cliente in clientes:
        cid = cliente.id
        ultima_visita = ultimas_visitas.get(cid)
        pesquisa = ultima_pesquisa.get(cid)
        contrato = contratos.get(cid)
        datas_saida = list(saidas.get(cid, {}).values())

        sinais = {
            "reclamacoes": len(reclamacoes.get(cid, [])),
            "chamados_parados": chamados_parados.get(cid, 0),
            "ultima_visita": ultima_visita.isoformat() if ultima_visita else None,
            "dias_sem_visita": (hoje - ultima_visita).days if ultima_visita else None,
            "turnos_vagos": turnos_vagos.get(cid, 0),
            "colaboradores_efetivos": colaboradores_efetivos.get(cid, 0),
            "postos_contratados": contrato.postos_contratados if contrato else None,
            "trocas_colaborador": len(datas_saida),
            "faltas": len(faltas.get(cid, [])),
            "custo_diarias": round(custo_diarias.get(cid, 0.0), 2),
            "ultima_nota": pesquisa.nota if pesquisa else None,
            "ultima_pesquisa": pesquisa.data_pesquisa.isoformat() if pesquisa else None,
        }

        eventos = reclamacoes.get(cid, []) + faltas.get(cid, []) + datas_saida
        recentes = sum(1 for d in eventos if d >= corte_tendencia)
        anteriores = len(eventos) - recentes
        if recentes - anteriores >= 2:
            tendencia = "piorando"
        elif anteriores - recentes >= 2:
            tendencia = "melhorando"
        else:
            tendencia = "estavel"
        sinais["eventos_negativos_recentes"] = recentes
        sinais["eventos_negativos_anteriores"] = anteriores

        motivos = _pontuar(sinais)
        score = max(0, 100 - sum(m["impacto"] for m in motivos))
        faixa = faixa_da_nota(score)

        if motivos:
            acao = CATEGORIAS_MOTIVO[motivos[0]["categoria"]]["acao"]
        elif pesquisa is None or (hoje - pesquisa.data_pesquisa).days > PESQUISA_DESATUALIZADA_DIAS:
            acao = "Aplicar pesquisa de satisfação para confirmar que está tudo bem"
        else:
            acao = "Manter a rotina de visitas"

        pendencias = []
        if contrato is None:
            pendencias.append("Sem contrato cadastrado")
        elif not contrato.valor_mensal:
            pendencias.append("Sem valor mensal no contrato")
        if not total_contatos.get(cid):
            pendencias.append("Sem contatos cadastrados")
        if cliente.supervisor_id is None:
            pendencias.append("Sem supervisor responsável")

        linhas.append({
            "cliente_id": cid,
            "cliente_nome": cliente.nome,
            "empresa_id": cliente.empresa_id,
            "empresa_nome": cliente.empresa.nome,
            "supervisor_id": cliente.supervisor_id,
            "supervisor_nome": cliente.supervisor.nome if cliente.supervisor else None,
            "score": score,
            "faixa": faixa["chave"],
            "faixa_label": faixa["label"],
            "tendencia": tendencia,
            "motivos": motivos,
            "acao_sugerida": acao,
            "sinais": sinais,
            "contrato": serializar_contrato(contrato),
            "alertas_contrato": alertas_do_contrato(contrato, hoje),
            "total_contatos": total_contatos.get(cid, 0),
            "pendencias_cadastro": pendencias,
        })

    return linhas


def _media(valores: list[float]) -> int | None:
    return round(sum(valores) / len(valores)) if valores else None


def _agrupar(linhas: list[dict], chave_id: str, chave_nome: str, rotulo_vazio: str) -> list[dict]:
    grupos: dict = {}
    for linha in linhas:
        grupo = grupos.setdefault(linha[chave_id], {
            "id": linha[chave_id],
            "nome": linha[chave_nome] or rotulo_vazio,
            "clientes": 0,
            "scores": [],
            "em_risco": 0,
            "atencao": 0,
            "sem_visita_30d": 0,
            "receita_mensal": 0.0,
        })
        grupo["clientes"] += 1
        grupo["scores"].append(linha["score"])
        if linha["faixa"] == "risco":
            grupo["em_risco"] += 1
        elif linha["faixa"] == "atencao":
            grupo["atencao"] += 1
        dias = linha["sinais"]["dias_sem_visita"]
        if dias is None or dias > 30:
            grupo["sem_visita_30d"] += 1
        if linha["contrato"] and linha["contrato"]["valor_mensal"]:
            grupo["receita_mensal"] += linha["contrato"]["valor_mensal"]

    resultado = []
    for grupo in grupos.values():
        grupo["score_medio"] = _media(grupo.pop("scores"))
        grupo["receita_mensal"] = round(grupo["receita_mensal"], 2)
        resultado.append(grupo)
    resultado.sort(key=lambda g: (g["score_medio"], -g["clientes"]))
    return resultado


def resumir_carteira(linhas: list[dict], notas_nps: list[int]) -> dict:
    """
    Junta a saude de todos os clientes em: indicadores, distribuicao por
    faixa, visao por empresa/supervisor, lista de prioridades e frases de
    leitura rapida (insights) - o que um gestor precisa ler em 1 minuto.
    notas_nps: ultima nota de cada cliente avaliado dentro da janela.
    """
    total = len(linhas)
    em_risco = [l for l in linhas if l["faixa"] == "risco"]
    atencao = [l for l in linhas if l["faixa"] == "atencao"]
    saudaveis = total - len(em_risco) - len(atencao)

    def valor(linha):
        return (linha["contrato"] or {}).get("valor_mensal") or 0.0

    receita_total = sum(valor(l) for l in linhas)
    receita_risco = sum(valor(l) for l in em_risco)
    receita_atencao = sum(valor(l) for l in atencao)
    com_valor = sum(1 for l in linhas if valor(l) > 0)
    com_contrato = sum(1 for l in linhas if l["contrato"])

    alertas_contrato = [(l, a) for l in linhas for a in l["alertas_contrato"]]
    vencendo_90d = [(l, a) for l, a in alertas_contrato if a["tipo"] == "vigencia" and a["urgencia"] in ("alta", "media")]
    reajustes = [(l, a) for l, a in alertas_contrato if a["tipo"] == "reajuste" and a["urgencia"] == "alta"]

    nps = calcular_nps(notas_nps)

    indicadores = {
        "clientes": total,
        "score_medio": _media([l["score"] for l in linhas]),
        "saudaveis": saudaveis,
        "atencao": len(atencao),
        "em_risco": len(em_risco),
        "piorando": sum(1 for l in linhas if l["tendencia"] == "piorando"),
        "melhorando": sum(1 for l in linhas if l["tendencia"] == "melhorando"),
        "receita_mensal": round(receita_total, 2),
        "receita_em_risco": round(receita_risco, 2),
        "receita_em_atencao": round(receita_atencao, 2),
        "clientes_com_contrato": com_contrato,
        "clientes_com_valor": com_valor,
        "contratos_vencendo_90d": len(vencendo_90d),
        "receita_vencendo_90d": round(sum(valor(l) for l, _ in vencendo_90d), 2),
        "reajustes_pendentes": len(reajustes),
        "nps": nps,
        "nps_base": len(notas_nps),
    }

    insights = []
    if total:
        if em_risco:
            texto = (f"{_plural(len(em_risco), 'cliente está', 'clientes estão')} em risco "
                     f"({round(len(em_risco) * 100 / total)}% da carteira)")
            if receita_risco:
                texto += f", somando {formatar_moeda(receita_risco)}/mês de receita"
            sem_valor = sum(1 for l in em_risco if valor(l) == 0)
            if sem_valor:
                texto += f" — {sem_valor} deles sem valor de contrato cadastrado"
            insights.append({"nivel": "alerta", "texto": texto + "."})
        else:
            insights.append({"nivel": "positivo", "texto": "Nenhum cliente está na faixa de risco neste momento."})

        contagem_categoria: dict[str, int] = {}
        for l in linhas:
            for m in l["motivos"]:
                contagem_categoria[m["categoria"]] = contagem_categoria.get(m["categoria"], 0) + 1
        if contagem_categoria:
            categoria, qtd = max(contagem_categoria.items(), key=lambda x: x[1])
            insights.append({"nivel": "atencao", "texto": (
                f"O fator que mais pesa na carteira é \"{CATEGORIAS_MOTIVO[categoria]['label'].lower()}\", "
                f"presente em {_plural(qtd, 'cliente', 'clientes')}. "
                f"Ação recomendada: {CATEGORIAS_MOTIVO[categoria]['acao'].lower()}."
            )})

        piorando = indicadores["piorando"]
        melhorando = indicadores["melhorando"]
        if piorando or melhorando:
            nivel = "atencao" if piorando > melhorando else "positivo"
            insights.append({"nivel": nivel, "texto": (
                f"Nos últimos {JANELA_TENDENCIA_DIAS} dias, {_plural(piorando, 'cliente piorou', 'clientes pioraram')} "
                f"e {_plural(melhorando, 'melhorou', 'melhoraram')} em relação aos {JANELA_TENDENCIA_DIAS} dias anteriores."
            )})

        # supervisor que concentra mais clientes fora da faixa saudavel
        por_supervisor = _agrupar(linhas, "supervisor_id", "supervisor_nome", "Sem supervisor")
        criticos = [g for g in por_supervisor if g["em_risco"]]
        if len(em_risco) >= 2 and criticos:
            pior = max(criticos, key=lambda g: (g["em_risco"], -g["score_medio"]))
            insights.append({"nivel": "atencao", "texto": (
                f"A carteira de {pior['nome']} concentra {pior['em_risco']} dos {len(em_risco)} clientes em risco "
                f"(nota média {pior['score_medio']} em {_plural(pior['clientes'], 'cliente', 'clientes')})."
            )})

        sem_visita = sum(1 for l in linhas if l["sinais"]["dias_sem_visita"] is None or l["sinais"]["dias_sem_visita"] > 30)
        if sem_visita:
            insights.append({"nivel": "atencao" if sem_visita * 3 > total else "info", "texto": (
                f"{_plural(sem_visita, 'cliente está', 'clientes estão')} há mais de 30 dias sem visita de supervisão "
                f"({round(sem_visita * 100 / total)}% da carteira)."
            )})

        if vencendo_90d:
            texto = f"{_plural(len(vencendo_90d), 'contrato vence', 'contratos vencem')} nos próximos 90 dias"
            if indicadores["receita_vencendo_90d"]:
                texto += f" ({formatar_moeda(indicadores['receita_vencendo_90d'])}/mês)"
            ruins = sum(1 for l, _ in vencendo_90d if l["faixa"] != "saudavel")
            if ruins:
                texto += f" — {ruins} deles com saúde abaixo de saudável, cuidado na renovação"
            insights.append({"nivel": "alerta" if ruins else "info", "texto": texto + "."})

        if reajustes:
            insights.append({"nivel": "alerta", "texto": (
                f"{_plural(len(reajustes), 'reajuste está atrasado ou vence', 'reajustes estão atrasados ou vencem')} "
                f"em até 30 dias. Reajuste esquecido é receita perdida todo mês."
            )})

        if nps is not None:
            nivel = "positivo" if nps >= 50 else "info" if nps >= 0 else "alerta"
            insights.append({"nivel": nivel, "texto": (
                f"NPS da carteira: {'+' if nps > 0 else ''}{nps}, com base em {_plural(len(notas_nps), 'cliente avaliado', 'clientes avaliados')} "
                f"nos últimos 12 meses ({round(len(notas_nps) * 100 / total)}% da carteira)."
            )})
        else:
            insights.append({"nivel": "info", "texto": "Nenhuma pesquisa de satisfação registrada nos últimos 12 meses — sem ela, a nota de saúde enxerga só os sinais operacionais."})

        if com_valor < total:
            insights.append({"nivel": "info", "texto": (
                f"Só {com_valor} de {total} clientes têm valor de contrato cadastrado. "
                f"Complete os contratos para medir a receita em risco com precisão."
            )})

    # uma entrada por cliente, juntando os motivos (saude e contrato) e as acoes
    por_cliente: dict[int, dict] = {}

    def priorizar(linha: dict, urgencia: str, motivo: str, acao: str):
        item = por_cliente.setdefault(linha["cliente_id"], {
            "cliente_id": linha["cliente_id"], "cliente_nome": linha["cliente_nome"], "empresa_nome": linha["empresa_nome"],
            "supervisor_nome": linha["supervisor_nome"], "urgencia": urgencia, "score": linha["score"],
            "valor_mensal": valor(linha) or None, "motivos": [], "acoes": [],
        })
        if urgencia == "alta":
            item["urgencia"] = "alta"
        item["motivos"].append(motivo)
        if acao not in item["acoes"]:
            item["acoes"].append(acao)

    for l in em_risco:
        priorizar(l, "alta", l["motivos"][0]["texto"] if l["motivos"] else "Nota de saúde baixa", l["acao_sugerida"])
    for l, a in alertas_contrato:
        if a["urgencia"] != "alta":
            continue
        acao = "Aplicar o reajuste e comunicar o cliente" if a["tipo"] == "reajuste" else "Negociar a renovação do contrato"
        priorizar(l, "alta", a["texto"], acao)
    for l in atencao:
        if l["tendencia"] != "piorando":
            continue
        priorizar(l, "media", "Piorando: " + (l["motivos"][0]["texto"] if l["motivos"] else "mais ocorrências recentes"),
                  l["acao_sugerida"])

    prioridades = []
    for item in por_cliente.values():
        item["motivo"] = " · ".join(item.pop("motivos"))
        item["acao"] = "; ".join(item.pop("acoes"))
        prioridades.append(item)
    ordem_urgencia = {"alta": 0, "media": 1}
    prioridades.sort(key=lambda p: (ordem_urgencia[p["urgencia"]], p["score"], -(p["valor_mensal"] or 0)))

    return {
        "indicadores": indicadores,
        "insights": insights,
        "prioridades": prioridades[:15],
        "total_prioridades": len(prioridades),
        "por_empresa": _agrupar(linhas, "empresa_id", "empresa_nome", "Sem empresa"),
        "por_supervisor": _agrupar(linhas, "supervisor_id", "supervisor_nome", "Sem supervisor"),
    }


def notas_nps_vigentes(db: Session, cliente_ids: list[int]) -> dict[int, int]:
    """Ultima nota de cada cliente dentro da janela de pesquisa (base do NPS da carteira)."""
    limite = date.today() - timedelta(days=JANELA_PESQUISA_DIAS)
    ultimas: dict[int, int] = {}
    for cliente_id, nota in (
        db.query(PesquisaSatisfacao.cliente_id, PesquisaSatisfacao.nota)
        .filter(PesquisaSatisfacao.cliente_id.in_(cliente_ids), PesquisaSatisfacao.data_pesquisa >= limite)
        .order_by(PesquisaSatisfacao.data_pesquisa.desc(), PesquisaSatisfacao.id.desc())
        .all()
    ):
        ultimas.setdefault(cliente_id, nota)
    return ultimas
