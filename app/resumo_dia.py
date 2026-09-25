"""
Resumo analitico de um dia de operacao (aba "Resumo do dia" do CRM e PDF).

Junta tudo que aconteceu no dia - chamados, visitas, faltas, horas de
falta, atestados, diarias de cobertura, custos, entradas/saidas de
colaboradores nos postos, postos vagos, estoque e pesquisas - compara com
a media dos mesmos dias da semana nas 4 semanas anteriores e cruza por
cliente (com a nota de saude do CRM) pra apontar onde o gestor precisa
olhar. As frases de leitura (insights) sao montadas aqui, em cima dos
numeros, pra tela e PDF dizerem exatamente a mesma coisa.

O "dia" e o dia civil no horario de Brasilia (UTC-3, sem horario de
verao desde 2019): os timestamps do banco sao UTC e sao convertidos antes
de agrupar.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from crm_saude import NOME_CLIENTE_INTERNO, alertas_do_contrato, calcular_saude_carteira, formatar_moeda
from models import (
    Chamado,
    Cliente,
    ClienteContrato,
    Colaborador,
    ColaboradorEvento,
    ConfirmacaoPostoVago,
    CustoDiario,
    EstoqueItem,
    EstoqueMovimento,
    HistoricoMapaServico,
    HorarioServico,
    PesquisaSatisfacao,
    TarefaAgendada,
    Usuario,
    VagaAberta,
    VisitaSupervisao,
)

FUSO_BRASILIA = timezone(timedelta(hours=-3))
SEMANAS_BASE = 4  # media dos mesmos dias da semana nas ultimas 4 semanas
ESTOQUE_BAIXO = 2
DIAS_SEMANA_NOME = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
DIAS_SEMANA_PLURAL = ["segundas", "terças", "quartas", "quintas", "sextas", "sábados", "domingos"]
DIAS_SEMANA_CHAVE = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
STATUS_DIARIA_FALTA = {"falta", "atestado", "posto_vago"}
PRIORIDADES_URGENTES = {"urgente", "urgentissimo"}

# peso de cada ocorrencia no "ponto de atencao" do cliente no dia
PESO_OCORRENCIA = {
    "reclamacao": 3,
    "detrator": 3,
    "chamado_urgente": 2,
    "falta": 2,
    "saida": 2,
    "posto_vago": 2,
    "chamado": 1,
}


def hoje_brasilia() -> date:
    return datetime.now(FUSO_BRASILIA).date()


def _para_utc(dia: date) -> datetime:
    return datetime.combine(dia, time.min, tzinfo=FUSO_BRASILIA).astimezone(timezone.utc)


def _local(momento: datetime) -> datetime:
    # o Postgres devolve com fuso; se vier sem (ex: sqlite de teste), e UTC
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(FUSO_BRASILIA)


def _plural(n, singular: str, plural: str) -> str:
    numero = f"{n:g}" if isinstance(n, float) else str(n)
    return f"{numero} {singular if n == 1 else plural}"


def formatar_horas(horas: float) -> str:
    inteiras = int(horas)
    minutos = round((horas - inteiras) * 60)
    return f"{inteiras}h{minutos:02d}" if minutos else f"{inteiras}h"


def _num(valor: float) -> str:
    return f"{valor:g}".replace(".", ",")


def _ha_dias(dias: int) -> str:
    return "aberto hoje" if dias <= 0 else "aberto ontem" if dias == 1 else f"há {dias} dias"


def _comparar(valor: float, media: float, rotulo_media: str) -> dict:
    """Compara o valor do dia com a media e devolve direcao + texto curto."""
    diferenca = valor - media
    limite = max(1.0, media * 0.25)  # variacao menor que 25% (ou 1) e considerada normal
    if diferenca > limite:
        direcao = "acima"
    elif diferenca < -limite:
        direcao = "abaixo"
    else:
        direcao = "normal"
    return {"media": round(media, 1), "direcao": direcao, "rotulo": rotulo_media}


def _intervalo_cobre(dia: date, inicio: date | None, fim: date | None) -> bool:
    if inicio is None:
        return False
    return inicio <= dia <= (fim or inicio)


def montar_resumo_dia(
    db: Session,
    dia: date,
    labels_tipo_chamado: dict[str, str],
    labels_status_diaria: dict[str, str],
    labels_tipo_custo: dict[str, str],
) -> dict:
    inicio_utc = _para_utc(dia)
    fim_utc = _para_utc(dia + timedelta(days=1))
    amanha = dia + timedelta(days=1)
    dias_base = [dia - timedelta(weeks=s) for s in range(1, SEMANAS_BASE + 1)]
    inicio_base = min(dias_base)
    inicio_base_utc = _para_utc(inicio_base)
    rotulo_media = f"média das últimas {SEMANAS_BASE} {DIAS_SEMANA_PLURAL[dia.weekday()]}"

    cliente_interno_id = db.query(Cliente.id).filter(Cliente.nome == NOME_CLIENTE_INTERNO).scalar()
    posto_vago = db.query(Colaborador).filter_by(eh_posto_vago=True).first()
    posto_vago_id = posto_vago.id if posto_vago else -1

    # ------------------------------------------------------------------
    # Chamados: abertos e finalizados no dia, backlog no fim do dia
    # ------------------------------------------------------------------
    chamados_periodo = (
        db.query(Chamado)
        .filter(Chamado.criado_em >= inicio_base_utc, Chamado.criado_em < fim_utc)
        .all()
    )
    abertos_dia = [c for c in chamados_periodo if _local(c.criado_em).date() == dia]
    abertos_base = {d: 0 for d in dias_base}
    reclamacoes_base = {d: 0 for d in dias_base}
    for c in chamados_periodo:
        d = _local(c.criado_em).date()
        if d in abertos_base:
            abertos_base[d] += 1
            if c.tipo == "reclamacao":
                reclamacoes_base[d] += 1

    finalizados_dia = (
        db.query(Chamado)
        .filter(Chamado.finalizado_em >= inicio_utc, Chamado.finalizado_em < fim_utc)
        .all()
    )
    # backlog como estava no fim do dia (vale tambem pra dias passados)
    backlog = (
        db.query(Chamado)
        .filter(Chamado.criado_em < fim_utc, or_(Chamado.finalizado_em.is_(None), Chamado.finalizado_em >= fim_utc))
        .all()
    )
    backlog_urgente = sorted(
        (c for c in backlog if c.prioridade in PRIORIDADES_URGENTES), key=lambda c: c.criado_em
    )
    fim_local = datetime.combine(amanha, time.min, tzinfo=FUSO_BRASILIA)

    def serializar_chamado_dia(c: Chamado) -> dict:
        return {
            "id": c.id,
            "hora": _local(c.criado_em).strftime("%H:%M"),
            "cliente_id": c.cliente_id,
            "cliente_nome": c.cliente.nome,
            "tipo": c.tipo,
            "tipo_label": labels_tipo_chamado.get(c.tipo, c.tipo),
            "prioridade": c.prioridade,
            "descricao": c.descricao,
            "aberto_por": c.aberto_por.nome,
            "responsavel": c.responsavel.nome if c.responsavel else None,
            "status": c.status,
            "dias_em_aberto": (fim_local - _local(c.criado_em)).days,
        }

    horas_resolucao = [
        (c.finalizado_em - c.criado_em).total_seconds() / 3600 for c in finalizados_dia if c.criado_em
    ]

    # ------------------------------------------------------------------
    # Visitas de supervisao
    # ------------------------------------------------------------------
    visitas_periodo = (
        db.query(VisitaSupervisao)
        .filter(VisitaSupervisao.data_visita >= inicio_base, VisitaSupervisao.data_visita <= dia)
        .all()
    )
    visitas_dia = [v for v in visitas_periodo if v.data_visita == dia]
    visitas_base = {d: sum(1 for v in visitas_periodo if v.data_visita == d) for d in dias_base}

    # ------------------------------------------------------------------
    # Faltas, horas de falta, atestados, ferias e advertencias
    # ------------------------------------------------------------------
    eventos_colab = (
        db.query(ColaboradorEvento)
        .filter(
            ColaboradorEvento.tipo.in_(["falta", "horas_falta", "atestado", "ferias", "advertencia"]),
            or_(
                ColaboradorEvento.data_inicio <= dia,
                ColaboradorEvento.criado_em >= inicio_utc,
            ),
            or_(
                ColaboradorEvento.data_fim.is_(None),
                ColaboradorEvento.data_fim >= inicio_base,
            ),
        )
        .all()
    )
    faltas_dia = [e for e in eventos_colab if e.tipo == "falta" and _intervalo_cobre(dia, e.data_inicio, e.data_fim)]
    horas_falta_dia = [e for e in eventos_colab if e.tipo == "horas_falta" and e.data_inicio == dia]
    atestados_dia = [e for e in eventos_colab if e.tipo == "atestado" and _intervalo_cobre(dia, e.data_inicio, e.data_fim)]
    ferias_dia = [e for e in eventos_colab if e.tipo == "ferias" and _intervalo_cobre(dia, e.data_inicio, e.data_fim)]
    advertencias_dia = [e for e in eventos_colab if e.tipo == "advertencia" and _local(e.criado_em).date() == dia]
    faltas_base = {
        d: sum(1 for e in eventos_colab if e.tipo == "falta" and _intervalo_cobre(d, e.data_inicio, e.data_fim))
        for d in dias_base
    }
    total_horas_falta = round(sum(e.horas or 0 for e in horas_falta_dia), 2)

    # ------------------------------------------------------------------
    # Custos do dia: diarias de cobertura e demais despesas
    # ------------------------------------------------------------------
    custos_periodo = (
        db.query(CustoDiario).filter(CustoDiario.data >= inicio_base, CustoDiario.data <= dia).all()
    )
    custos_dia = [c for c in custos_periodo if c.data == dia]
    diarias_dia = [c for c in custos_dia if c.status_diaria]
    outros_custos_dia = [c for c in custos_dia if not c.status_diaria]
    custo_total_base = {d: sum(c.valor or 0 for c in custos_periodo if c.data == d) for d in dias_base}
    diarias_base = {d: sum(1 for c in custos_periodo if c.data == d and c.status_diaria) for d in dias_base}
    custo_total_dia = round(sum(c.valor or 0 for c in custos_dia), 2)
    custo_diarias_dia = round(sum(c.valor or 0 for c in diarias_dia), 2)
    custos_por_tipo: dict[str, float] = {}
    for c in outros_custos_dia:
        rotulo = labels_tipo_custo.get(c.tipo, c.tipo)
        custos_por_tipo[rotulo] = custos_por_tipo.get(rotulo, 0) + (c.valor or 0)

    pendentes_reembolso = db.query(CustoDiario).filter(CustoDiario.reembolsado.is_(False)).all()

    # faltas de dia inteiro sem ninguem apontado como cobertura (nem colaborador, nem diaria no mesmo cliente)
    clientes_com_diaria = {c.cliente_id for c in diarias_dia if c.cliente_id}
    faltas_sem_cobertura = [
        e for e in faltas_dia
        if e.colaborador_relacionado_id is None and not e.colaborador_relacionado_nome_manual
        and (e.colaborador.cliente_id is None or e.colaborador.cliente_id not in clientes_com_diaria)
    ]

    # ------------------------------------------------------------------
    # Equipe nos postos (mapa de servico), admissoes e desligamentos
    # ------------------------------------------------------------------
    movimentos_mapa = (
        db.query(HistoricoMapaServico)
        .filter(HistoricoMapaServico.criado_em >= inicio_utc, HistoricoMapaServico.criado_em < fim_utc,
                HistoricoMapaServico.tipo_evento.in_(["iniciado", "encerrado"]),
                HistoricoMapaServico.colaborador_id != posto_vago_id)
        .all()
    )
    entradas_posto: dict[tuple, HistoricoMapaServico] = {}
    saidas_posto: dict[tuple, HistoricoMapaServico] = {}
    for m in movimentos_mapa:
        destino = entradas_posto if m.tipo_evento == "iniciado" else saidas_posto
        destino.setdefault((m.colaborador_id, m.cliente_id), m)

    admitidos = db.query(Colaborador).filter(Colaborador.data_admissao == dia, Colaborador.eh_posto_vago.is_(False)).all()
    desligados = db.query(Colaborador).filter(Colaborador.data_desligamento == dia, Colaborador.eh_posto_vago.is_(False)).all()

    def turnos_vagos_em(alvo: date) -> list[HorarioServico]:
        return (
            db.query(HorarioServico)
            .join(Cliente, HorarioServico.cliente_id == Cliente.id)
            .filter(HorarioServico.colaborador_id == posto_vago_id,
                    HorarioServico.dia_semana == DIAS_SEMANA_CHAVE[alvo.weekday()],
                    HorarioServico.data_inicio <= alvo,
                    or_(HorarioServico.data_fim.is_(None), HorarioServico.data_fim > alvo),
                    Cliente.ativo.is_(True))
            .all()
        )

    vagos_dia = turnos_vagos_em(dia)
    vagos_amanha = turnos_vagos_em(amanha)
    confirmados_amanha = {
        c.cliente_id for c in db.query(ConfirmacaoPostoVago).filter(ConfirmacaoPostoVago.data_alvo == amanha).all()
    }

    # ------------------------------------------------------------------
    # Estoque, pesquisas, tarefas e vagas
    # ------------------------------------------------------------------
    movimentos_estoque = (
        db.query(EstoqueMovimento)
        .filter(EstoqueMovimento.criado_em >= inicio_utc, EstoqueMovimento.criado_em < fim_utc)
        .all()
    )
    saidas_estoque = [m for m in movimentos_estoque if m.tipo == "saida"]
    entradas_estoque = [m for m in movimentos_estoque if m.tipo == "entrada"]
    itens_saida = {m.item_id for m in saidas_estoque}
    estoque_baixo = (
        db.query(EstoqueItem)
        .filter(EstoqueItem.id.in_(itens_saida), EstoqueItem.quantidade_atual <= ESTOQUE_BAIXO)
        .all()
    ) if itens_saida else []

    pesquisas_dia = db.query(PesquisaSatisfacao).filter(PesquisaSatisfacao.data_pesquisa == dia).all()
    tarefas_amanha = (
        db.query(TarefaAgendada)
        .filter(TarefaAgendada.data == amanha, TarefaAgendada.concluida.is_(False))
        .order_by(TarefaAgendada.titulo)
        .all()
    )
    tarefas_atrasadas = (
        db.query(TarefaAgendada).filter(TarefaAgendada.data <= dia, TarefaAgendada.concluida.is_(False)).count()
    )
    vagas_novas = (
        db.query(VagaAberta).filter(VagaAberta.criado_em >= inicio_utc, VagaAberta.criado_em < fim_utc).all()
    )
    vagas_abertas = db.query(VagaAberta).filter(VagaAberta.aberta.is_(True)).count()

    # ------------------------------------------------------------------
    # Cruzamento por cliente: onde o dia concentrou problemas
    # ------------------------------------------------------------------
    ocorrencias: dict[int, dict] = {}

    def ocorrer(cliente: Cliente | None, categoria: str, texto: str, valor: float = 0.0):
        if cliente is None or cliente.id == cliente_interno_id:
            return
        registro = ocorrencias.setdefault(cliente.id, {
            "cliente_id": cliente.id, "cliente_nome": cliente.nome, "empresa_nome": cliente.empresa.nome,
            "supervisor_nome": cliente.supervisor.nome if cliente.supervisor else None,
            "pontos": 0, "itens": [], "custo": 0.0, "visitado": False,
        })
        registro["pontos"] += PESO_OCORRENCIA.get(categoria, 1)
        registro["itens"].append({"categoria": categoria, "texto": texto})
        registro["custo"] += valor

    for c in abertos_dia:
        if c.tipo == "reclamacao":
            ocorrer(c.cliente, "reclamacao", f"Reclamação: {c.descricao[:90]}")
        elif c.prioridade in PRIORIDADES_URGENTES:
            ocorrer(c.cliente, "chamado_urgente", f"Chamado urgente: {labels_tipo_chamado.get(c.tipo, c.tipo)}")
        else:
            ocorrer(c.cliente, "chamado", f"Chamado: {labels_tipo_chamado.get(c.tipo, c.tipo)}")
    for c in diarias_dia:
        if c.status_diaria in STATUS_DIARIA_FALTA:
            ocorrer(c.cliente, "falta",
                    f"Diária de cobertura ({labels_status_diaria.get(c.status_diaria, c.status_diaria).lower()}) — {formatar_moeda(c.valor or 0)}",
                    c.valor or 0)
    for e in faltas_dia:
        if e.colaborador.cliente is not None and e.colaborador.cliente_id not in clientes_com_diaria:
            ocorrer(e.colaborador.cliente, "falta", f"Falta de {e.colaborador.nome}")
    for m in saidas_posto.values():
        ocorrer(m.cliente, "saida", f"{m.colaborador.nome} saiu do posto" + (f" ({m.motivo})" if m.motivo else ""))
    por_cliente_vago: dict[int, int] = {}
    for h in vagos_dia:
        por_cliente_vago[h.cliente_id] = por_cliente_vago.get(h.cliente_id, 0) + 1
    for cliente_id, qtd in por_cliente_vago.items():
        ocorrer(db.get(Cliente, cliente_id), "posto_vago", f"{_plural(qtd, 'turno vago', 'turnos vagos')} hoje")
    for p in pesquisas_dia:
        if p.nota <= 6:
            ocorrer(p.cliente, "detrator", f"Avaliação {p.nota}/10" + (f": \"{p.comentario[:80]}\"" if p.comentario else ""))
    for v in visitas_dia:
        if v.cliente_id in ocorrencias:
            ocorrencias[v.cliente_id]["visitado"] = True

    saude_por_cliente = {}
    if ocorrencias:
        saude_por_cliente = {l["cliente_id"]: l for l in calcular_saude_carteira(db, list(ocorrencias.keys()))}

    pontos_atencao = []
    for registro in ocorrencias.values():
        saude = saude_por_cliente.get(registro["cliente_id"])
        registro["score"] = saude["score"] if saude else None
        registro["faixa"] = saude["faixa"] if saude else None
        registro["faixa_label"] = saude["faixa_label"] if saude else None
        registro["valor_mensal"] = ((saude or {}).get("contrato") or {}).get("valor_mensal")
        registro["custo"] = round(registro["custo"], 2)
        # cliente que ja estava fraco pesa mais: o problema do dia se soma ao historico
        if registro["faixa"] == "risco":
            registro["pontos"] += 3
        elif registro["faixa"] == "atencao":
            registro["pontos"] += 1
        categorias = {i["categoria"] for i in registro["itens"]}
        if registro["faixa"] == "risco":
            leitura = f"Já estava em risco (nota {registro['score']}): o dia agravou um cliente frágil."
        elif len(categorias) >= 2:
            leitura = "Problemas de naturezas diferentes no mesmo dia: vale uma ligação para o responsável."
        elif "reclamacao" in categorias or "detrator" in categorias:
            leitura = "O cliente se manifestou: responda ainda hoje para não virar desgaste."
        else:
            leitura = "Ocorrência operacional pontual: acompanhe se repete."
        if not registro["visitado"] and registro["pontos"] >= 5:
            leitura += " Sem visita de supervisão registrada hoje."
        registro["leitura"] = leitura
        registro["nivel"] = "alerta" if registro["pontos"] >= 6 else "atencao" if registro["pontos"] >= 3 else "info"
        pontos_atencao.append(registro)
    pontos_atencao.sort(key=lambda r: (-r["pontos"], -(r["valor_mensal"] or 0)))

    # ------------------------------------------------------------------
    # Atividade por supervisor
    # ------------------------------------------------------------------
    supervisores = db.query(Usuario).filter(Usuario.papel == "supervisor", Usuario.ativo.is_(True)).order_by(Usuario.nome).all()
    por_supervisor = []
    for s in supervisores:
        clientes_ocorrencia = [r for r in pontos_atencao if r["supervisor_nome"] == s.nome]
        por_supervisor.append({
            "id": s.id,
            "nome": s.nome,
            "visitas": sum(1 for v in visitas_dia if v.supervisor_id == s.id),
            "chamados_abertos": sum(1 for c in abertos_dia if c.aberto_por_id == s.id),
            "chamados_finalizados": sum(1 for c in finalizados_dia if c.finalizado_por_id == s.id),
            "diarias_lancadas": sum(1 for c in diarias_dia if c.usuario_id == s.id),
            "custos_lancados": round(sum(c.valor or 0 for c in custos_dia if c.usuario_id == s.id), 2),
            "clientes_com_ocorrencia": len(clientes_ocorrencia),
        })

    # ------------------------------------------------------------------
    # Indicadores com comparacao
    # ------------------------------------------------------------------
    def media(serie: dict) -> float:
        return sum(serie.values()) / len(serie) if serie else 0.0

    reclamacoes_dia = [c for c in abertos_dia if c.tipo == "reclamacao"]
    indicadores = {
        "chamados_abertos": {"valor": len(abertos_dia), **_comparar(len(abertos_dia), media(abertos_base), rotulo_media)},
        "chamados_finalizados": {"valor": len(finalizados_dia)},
        "backlog": {"valor": len(backlog), "urgentes": len(backlog_urgente)},
        "reclamacoes": {"valor": len(reclamacoes_dia), **_comparar(len(reclamacoes_dia), media(reclamacoes_base), rotulo_media)},
        "faltas": {"valor": len(faltas_dia), **_comparar(len(faltas_dia), media(faltas_base), rotulo_media)},
        "horas_falta": {"valor": total_horas_falta, "registros": len(horas_falta_dia)},
        "atestados": {"valor": len(atestados_dia)},
        "ferias": {"valor": len(ferias_dia)},
        "diarias": {"valor": len(diarias_dia), "custo": custo_diarias_dia, **_comparar(len(diarias_dia), media(diarias_base), rotulo_media)},
        "custo_total": {"valor": custo_total_dia, **_comparar(custo_total_dia, media(custo_total_base), rotulo_media)},
        "visitas": {"valor": len(visitas_dia), **_comparar(len(visitas_dia), media(visitas_base), rotulo_media)},
        "turnos_vagos": {"valor": len(vagos_dia), "amanha": len(vagos_amanha)},
        "tempo_medio_resolucao_horas": round(sum(horas_resolucao) / len(horas_resolucao), 1) if horas_resolucao else None,
    }

    # ------------------------------------------------------------------
    # Termometro e leitura do dia
    # ------------------------------------------------------------------
    alertas_graves = sum(1 for r in pontos_atencao if r["nivel"] == "alerta")
    acima = sum(1 for chave in ("chamados_abertos", "reclamacoes", "faltas", "diarias", "custo_total")
                if indicadores[chave].get("direcao") == "acima")
    if len(reclamacoes_dia) >= 3 or alertas_graves >= 2 or len(faltas_sem_cobertura) >= 2:
        status_dia = {"chave": "critico", "label": "Dia crítico"}
    elif reclamacoes_dia or alertas_graves or acima >= 2 or faltas_sem_cobertura:
        status_dia = {"chave": "atencao", "label": "Dia de atenção"}
    else:
        status_dia = {"chave": "tranquilo", "label": "Dia tranquilo"}

    dia_semana = DIAS_SEMANA_NOME[dia.weekday()]
    partes_manchete = [f"{_plural(len(abertos_dia), 'chamado aberto', 'chamados abertos')}"]
    if reclamacoes_dia:
        partes_manchete.append(_plural(len(reclamacoes_dia), "reclamação", "reclamações"))
    if faltas_dia or horas_falta_dia:
        texto_faltas = _plural(len(faltas_dia), "falta", "faltas")
        if total_horas_falta:
            texto_faltas += f" + {formatar_horas(total_horas_falta)} de falta parcial"
        partes_manchete.append(texto_faltas)
    if custo_total_dia:
        partes_manchete.append(f"{formatar_moeda(custo_total_dia)} em custos")
    manchete = ", ".join(partes_manchete) + "."
    teve_movimento = any([abertos_dia, finalizados_dia, visitas_dia, faltas_dia, horas_falta_dia, custos_dia,
                          movimentos_mapa, movimentos_estoque, pesquisas_dia])
    if not teve_movimento:
        manchete = "Nenhuma movimentação registrada no sistema neste dia."
    if pontos_atencao and pontos_atencao[0]["nivel"] != "info":
        manchete += f" Maior foco de atenção: {pontos_atencao[0]['cliente_nome']}."

    insights = []

    ind = indicadores["chamados_abertos"]
    saldo = len(abertos_dia) - len(finalizados_dia)
    texto = (f"Foram abertos {_plural(len(abertos_dia), 'chamado', 'chamados')} e finalizados {len(finalizados_dia)}"
             f" ({ind['rotulo']}: {_num(ind['media'])} por dia).")
    if saldo > 0:
        texto += f" O backlog cresceu {saldo} e fechou o dia com {len(backlog)} em aberto."
    elif saldo < 0:
        texto += f" O time fechou mais do que abriu: o backlog caiu {-saldo} e ficou em {len(backlog)}."
    else:
        texto += f" Backlog estável em {len(backlog)} chamados em aberto."
    if indicadores["tempo_medio_resolucao_horas"] is not None:
        texto += f" Tempo médio dos finalizados: {_num(indicadores['tempo_medio_resolucao_horas'])}h."
    insights.append({"nivel": "atencao" if ind["direcao"] == "acima" and saldo > 0 else "info", "texto": texto})

    if reclamacoes_dia:
        clientes = sorted({c.cliente.nome for c in reclamacoes_dia})
        insights.append({"nivel": "alerta", "texto": (
            f"{_plural(len(reclamacoes_dia), 'reclamação registrada', 'reclamações registradas')} "
            f"({', '.join(clientes[:4])}{'...' if len(clientes) > 4 else ''}). "
            f"Reclamação respondida no mesmo dia reduz muito o risco de cancelamento."
        )})
    else:
        insights.append({"nivel": "positivo", "texto": "Nenhuma reclamação de cliente registrada no dia."})

    if faltas_dia or horas_falta_dia or atestados_dia:
        texto = f"Ausências: {_plural(len(faltas_dia), 'falta', 'faltas')}"
        if horas_falta_dia:
            texto += f", {formatar_horas(total_horas_falta)} de falta parcial ({_plural(len(horas_falta_dia), 'registro', 'registros')})"
        texto += f" e {_plural(len(atestados_dia), 'atestado ativo', 'atestados ativos')}."
        if indicadores["faltas"]["direcao"] == "acima":
            texto += f" Acima do normal ({indicadores['faltas']['rotulo']}: {_num(indicadores['faltas']['media'])})."
        if faltas_sem_cobertura:
            nomes = ", ".join(e.colaborador.nome for e in faltas_sem_cobertura[:3])
            texto += f" Atenção: {_plural(len(faltas_sem_cobertura), 'falta sem cobertura registrada', 'faltas sem cobertura registrada')} ({nomes}) — confirme se o posto ficou descoberto."
        insights.append({"nivel": "alerta" if faltas_sem_cobertura else "atencao", "texto": texto})
    else:
        insights.append({"nivel": "positivo", "texto": "Nenhuma falta nem atestado registrado no dia."})

    if custo_total_dia:
        texto = f"Custos lançados: {formatar_moeda(custo_total_dia)}"
        if diarias_dia:
            texto += f", sendo {formatar_moeda(custo_diarias_dia)} em {_plural(len(diarias_dia), 'diária', 'diárias')} de cobertura"
        texto += "."
        comp = indicadores["custo_total"]
        if comp["direcao"] == "acima":
            texto += f" Acima do normal ({comp['rotulo']}: {formatar_moeda(comp['media'])})."
        elif comp["direcao"] == "abaixo":
            texto += f" Abaixo do normal ({comp['rotulo']}: {formatar_moeda(comp['media'])})."
        insights.append({"nivel": "atencao" if comp["direcao"] == "acima" else "info", "texto": texto})

    if dia.weekday() < 5 and supervisores:
        sem_visita = [s["nome"] for s in por_supervisor if s["visitas"] == 0]
        texto = f"{_plural(len(visitas_dia), 'visita de supervisão registrada', 'visitas de supervisão registradas')}."
        if sem_visita and len(sem_visita) < len(supervisores):
            texto += f" Sem visita registrada: {', '.join(sem_visita)}."
        elif sem_visita:
            texto += " Nenhum supervisor registrou visita — confirme se foram lançadas no sistema."
        insights.append({"nivel": "atencao" if sem_visita else "positivo", "texto": texto})

    if entradas_posto or saidas_posto or admitidos or desligados:
        partes = []
        if saidas_posto:
            partes.append(_plural(len(saidas_posto), "saída de posto", "saídas de posto"))
        if entradas_posto:
            partes.append(_plural(len(entradas_posto), "entrada em posto", "entradas em posto"))
        if admitidos:
            partes.append(_plural(len(admitidos), "admissão", "admissões"))
        if desligados:
            partes.append(_plural(len(desligados), "desligamento", "desligamentos"))
        insights.append({"nivel": "atencao" if len(saidas_posto) > len(entradas_posto) else "info",
                         "texto": "Movimentação de equipe: " + ", ".join(partes) + "."})

    if vagos_amanha:
        clientes_vagos = {h.cliente_id for h in vagos_amanha}
        sem_confirmacao = clientes_vagos - confirmados_amanha
        texto = f"Amanhã ({DIAS_SEMANA_NOME[amanha.weekday()]}) há {_plural(len(vagos_amanha), 'turno vago', 'turnos vagos')} em {_plural(len(clientes_vagos), 'cliente', 'clientes')}"
        texto += f", {len(sem_confirmacao)} ainda sem confirmação de cobertura." if sem_confirmacao else ", todos com cobertura confirmada."
        insights.append({"nivel": "alerta" if sem_confirmacao else "info", "texto": texto})

    if backlog_urgente:
        mais_antigo = backlog_urgente[0]
        insights.append({"nivel": "alerta", "texto": (
            f"{_plural(len(backlog_urgente), 'chamado urgente segue', 'chamados urgentes seguem')} em aberto; "
            f"o mais antigo é de {mais_antigo.cliente.nome}, {_ha_dias((fim_local - _local(mais_antigo.criado_em)).days)}."
        )})

    if estoque_baixo:
        itens = ", ".join(f"{i.tipo_peca} {i.tamanho} ({i.quantidade_atual})" for i in estoque_baixo[:4])
        insights.append({"nivel": "atencao", "texto": f"Estoque baixo depois das entregas do dia: {itens}. Programe reposição."})

    if pesquisas_dia:
        notas = [p.nota for p in pesquisas_dia]
        if len(notas) == 1:
            texto = f"1 avaliação de satisfação registrada ({pesquisas_dia[0].cliente.nome}): nota {notas[0]}."
        else:
            texto = f"{len(notas)} avaliações de satisfação registradas, média {_num(round(sum(notas) / len(notas), 1))}."
        detratores = [p.cliente.nome for p in pesquisas_dia if p.nota <= 6]
        if detratores:
            texto += f" Nota de detrator em {', '.join(detratores)}: retorne ao cliente."
        insights.append({"nivel": "alerta" if detratores else "positivo", "texto": texto})

    # ------------------------------------------------------------------
    # Pendencias para amanha
    # ------------------------------------------------------------------
    pendencias = []
    for cliente_id in sorted({h.cliente_id for h in vagos_amanha} - confirmados_amanha):
        cliente = db.get(Cliente, cliente_id)
        qtd = sum(1 for h in vagos_amanha if h.cliente_id == cliente_id)
        pendencias.append({"urgencia": "alta", "cliente_id": cliente_id, "texto": f"Cobrir {_plural(qtd, 'turno vago', 'turnos vagos')} em {cliente.nome}"})
    for c in backlog_urgente[:5]:
        pendencias.append({"urgencia": "alta", "cliente_id": c.cliente_id,
                           "texto": f"Chamado urgente em {c.cliente.nome}: {labels_tipo_chamado.get(c.tipo, c.tipo)} ({_ha_dias((fim_local - _local(c.criado_em)).days)})"})
    for r in pontos_atencao:
        if r["nivel"] == "alerta" and not r["visitado"]:
            pendencias.append({"urgencia": "media", "cliente_id": r["cliente_id"], "texto": f"Contato ou visita em {r['cliente_nome']} — {r['itens'][0]['texto']}"})
    for t in tarefas_amanha:
        pendencias.append({"urgencia": "media", "cliente_id": None, "texto": f"Tarefa agendada: {t.titulo}"})
    for contrato in db.query(ClienteContrato).all():
        for a in alertas_do_contrato(contrato, dia):
            if a["urgencia"] == "alta" and a["dias"] <= 7:
                pendencias.append({"urgencia": "media", "cliente_id": contrato.cliente_id,
                                   "texto": f"{contrato.cliente.nome}: {a['texto'].lower()}"})
    if pendentes_reembolso:
        total = sum(c.valor or 0 for c in pendentes_reembolso)
        pendencias.append({"urgencia": "baixa", "cliente_id": None,
                           "texto": f"{_plural(len(pendentes_reembolso), 'custo aguardando', 'custos aguardando')} reembolso ({formatar_moeda(total)})"})
    if tarefas_atrasadas:
        pendencias.append({"urgencia": "baixa", "cliente_id": None,
                           "texto": f"{_plural(tarefas_atrasadas, 'tarefa da agenda vencida', 'tarefas da agenda vencidas')} sem concluir"})

    # ------------------------------------------------------------------
    # Linha do tempo do dia (tudo em horario de Brasilia)
    # ------------------------------------------------------------------
    linha_do_tempo = []

    def marcar(momento: datetime, tipo: str, titulo: str, detalhe: str | None, sentimento: str = "neutro", cliente_id: int | None = None):
        local = _local(momento)
        if local.date() != dia:
            # lancado em outro dia (ex: visita registrada no dia seguinte): sem hora, no topo
            detalhe = f"{detalhe + ' · ' if detalhe else ''}lançado em {local.strftime('%d/%m %H:%M')}"
            hora, ordem = "—", "0"
        else:
            hora, ordem = local.strftime("%H:%M"), local.isoformat()
        linha_do_tempo.append({"hora": hora, "ordem": ordem,
                               "tipo": tipo, "titulo": titulo, "detalhe": detalhe, "sentimento": sentimento,
                               "cliente_id": cliente_id})

    for c in abertos_dia:
        marcar(c.criado_em, "chamado", f"Chamado aberto — {c.cliente.nome}",
               f"{labels_tipo_chamado.get(c.tipo, c.tipo)}: {c.descricao[:140]} (por {c.aberto_por.nome})",
               "negativo" if c.tipo == "reclamacao" or c.prioridade in PRIORIDADES_URGENTES else "neutro", c.cliente_id)
    for c in finalizados_dia:
        marcar(c.finalizado_em, "chamado", f"Chamado finalizado — {c.cliente.nome}",
               f"{labels_tipo_chamado.get(c.tipo, c.tipo)}" + (f" (por {c.finalizado_por.nome})" if c.finalizado_por else ""),
               "positivo", c.cliente_id)
    for v in visitas_dia:
        marcar(v.criado_em, "visita", f"Visita — {v.cliente.nome}",
               f"{v.supervisor.nome}" + (f" falou com {v.pessoa_com_quem_falou}" if v.pessoa_com_quem_falou else "")
               + (f": {v.observacoes[:140]}" if v.observacoes else ""), "positivo", v.cliente_id)
    for c in custos_dia:
        if c.status_diaria:
            titulo = f"Diária de cobertura — {c.cliente.nome if c.cliente else 'sem cliente'}"
            detalhe = f"{labels_status_diaria.get(c.status_diaria, c.status_diaria)} · {formatar_moeda(c.valor or 0)} · lançada por {c.usuario.nome}"
        else:
            titulo = f"Custo: {labels_tipo_custo.get(c.tipo, c.tipo)}"
            detalhe = f"{formatar_moeda(c.valor or 0)} · {c.usuario.nome}" + (f" · {c.descricao[:100]}" if c.descricao else "")
        marcar(c.criado_em, "custo", titulo, detalhe, "negativo" if c.status_diaria in STATUS_DIARIA_FALTA else "neutro", c.cliente_id)
    # atestado que comecou antes nao e novidade do dia - aparece so nos indicadores e ausencias
    for e in faltas_dia + horas_falta_dia + [a for a in atestados_dia if a.data_inicio == dia] + advertencias_dia:
        rotulo = {"falta": "Falta", "horas_falta": f"Horas falta ({formatar_horas(e.horas or 0)})",
                  "atestado": "Atestado", "advertencia": "Advertência"}[e.tipo]
        marcar(e.criado_em, "equipe", f"{rotulo} — {e.colaborador.nome}", e.descricao, "negativo",
               e.colaborador.cliente_id)
    for m in list(entradas_posto.values()) + list(saidas_posto.values()):
        entrou = m.tipo_evento == "iniciado"
        marcar(m.criado_em, "equipe", f"{'Entrou no posto' if entrou else 'Saiu do posto'} — {m.cliente.nome}",
               m.colaborador.nome + (f" ({m.motivo})" if m.motivo else ""), "neutro" if entrou else "negativo", m.cliente_id)
    for m in movimentos_estoque:
        destino = m.colaborador.nome if m.colaborador else (m.entregue_para_nome_manual or "")
        marcar(m.criado_em, "estoque", f"Estoque: {'saída' if m.tipo == 'saida' else 'entrada'} de {m.quantidade} {m.item.tipo_peca} {m.item.tamanho}",
               (f"para {destino}" if destino and m.tipo == "saida" else m.motivo), "neutro")
    for p in pesquisas_dia:
        marcar(p.criado_em, "pesquisa", f"Avaliação {p.nota}/10 — {p.cliente.nome}", p.comentario,
               "negativo" if p.nota <= 6 else "positivo" if p.nota >= 9 else "neutro", p.cliente_id)
    for v in vagas_novas:
        marcar(v.criado_em, "equipe", f"Vaga aberta: {v.titulo}", v.cliente.nome if v.cliente else None, "neutro", v.cliente_id)
    linha_do_tempo.sort(key=lambda t: t["ordem"])

    return {
        "data": dia.isoformat(),
        "dia_semana": dia_semana,
        "eh_hoje": dia == hoje_brasilia(),
        "status": status_dia,
        "manchete": manchete,
        "indicadores": indicadores,
        "insights": insights,
        "pontos_atencao": pontos_atencao[:12],
        "pendencias_amanha": pendencias,
        "por_supervisor": por_supervisor,
        "chamados_abertos": [serializar_chamado_dia(c) for c in sorted(abertos_dia, key=lambda c: c.criado_em)],
        "chamados_urgentes_em_aberto": [serializar_chamado_dia(c) for c in backlog_urgente[:10]],
        "ausencias": [
            {
                "colaborador_id": e.colaborador_id,
                "colaborador_nome": e.colaborador.nome,
                "cliente_nome": e.colaborador.cliente.nome if e.colaborador.cliente else None,
                "tipo": {"falta": "Falta", "horas_falta": "Horas falta", "atestado": "Atestado", "ferias": "Férias"}[e.tipo],
                "horas": e.horas if e.tipo == "horas_falta" else None,
                "cobertura": (e.colaborador_relacionado.nome if e.colaborador_relacionado else e.colaborador_relacionado_nome_manual),
                "sem_cobertura": e in faltas_sem_cobertura,
                "descricao": e.descricao,
            }
            for e in faltas_dia + horas_falta_dia + atestados_dia + ferias_dia
        ],
        "custos": {
            "total": custo_total_dia,
            "diarias": custo_diarias_dia,
            "por_tipo": [{"tipo": k, "valor": round(v, 2)} for k, v in sorted(custos_por_tipo.items(), key=lambda x: -x[1])],
            "diarias_detalhe": [
                {
                    "cliente_nome": c.cliente.nome if c.cliente else None,
                    "motivo": labels_status_diaria.get(c.status_diaria, c.status_diaria),
                    "quem_cobriu": (c.cobertura_colaborador.nome if c.cobertura_colaborador else
                                    c.freelancer.nome if c.freelancer else c.nome_beneficiario),
                    "valor": c.valor,
                    "lancado_por": c.usuario.nome,
                }
                for c in diarias_dia
            ],
            "pendentes_reembolso": round(sum(c.valor or 0 for c in pendentes_reembolso), 2),
        },
        "equipe": {
            "entradas_posto": len(entradas_posto),
            "saidas_posto": len(saidas_posto),
            "admitidos": [c.nome for c in admitidos],
            "desligados": [c.nome for c in desligados],
            "vagas_abertas": vagas_abertas,
        },
        "estoque": {
            "saidas": sum(m.quantidade for m in saidas_estoque),
            "entradas": sum(m.quantidade for m in entradas_estoque),
            "itens_baixos": [f"{i.tipo_peca} {i.tamanho}: {i.quantidade_atual}" for i in estoque_baixo],
        },
        "linha_do_tempo": linha_do_tempo,
        "gerado_em": datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y %H:%M"),
    }
