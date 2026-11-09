"""
Reconstroi o historico de trocas de colaborador no mapa de servico.

Ate esta correcao, trocar o colaborador de um posto (tela do cliente)
sobrescrevia o vinculo existente: a linha de horarios_servico passava a
apontar pro colaborador novo e o antigo sumia do historico (ficava so no
log historico_mapa_servico, como evento "editado").

Este script le esse log e, para cada vinculo em que o colaborador mudou
num evento "editado", recria o vinculo encerrado do colaborador anterior
(data_inicio = inicio do trecho, data_fim = dia da troca) e ajusta a
data_inicio do vinculo atual para o dia da troca. Os eventos do trecho
antigo passam a apontar pro vinculo recriado.

Limite: so da pra reconstruir o que o log registrou. Trocas feitas antes
de migrar_historico_mapa_servico.py existir nao tem como ser recuperadas.

Idempotente: depois de rodar, cada vinculo so tem eventos de um mesmo
colaborador, entao rodar de novo nao faz nada.

COMO USAR
---------
Primeiro so pra ver o que seria feito (nao grava nada):
    docker compose exec app python migrar_reconstruir_trocas_mapa.py --simular
Depois pra valer:
    docker compose exec app python migrar_reconstruir_trocas_mapa.py
"""

import sys
from datetime import timedelta, timezone

from sqlalchemy import func

from database import SessionLocal
from models import HistoricoMapaServico, HorarioServico

BRASILIA = timezone(timedelta(hours=-3))
MOTIVO = "Troca de colaborador (reconstruído do log)"


def data_brasilia(momento):
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(BRASILIA).date()


def reconstruir(db, horario: HorarioServico, eventos: list[HistoricoMapaServico]) -> int:
    trocas = 0
    inicio_trecho = horario.data_inicio
    colaborador_trecho = eventos[0].colaborador_id
    eventos_trecho = []
    ultimo_estado = eventos[0]

    for evento in eventos:
        if evento.tipo_evento == "editado" and evento.colaborador_id != colaborador_trecho:
            data_troca = max(data_brasilia(evento.criado_em), inicio_trecho)

            antigo = HorarioServico(
                colaborador_id=colaborador_trecho,
                cliente_id=horario.cliente_id,
                dia_semana=ultimo_estado.dia_semana,
                turno=ultimo_estado.turno,
                hora_inicio=ultimo_estado.hora_inicio,
                hora_fim=ultimo_estado.hora_fim,
                data_inicio=inicio_trecho,
                data_fim=data_troca,
            )
            db.add(antigo)
            db.flush()
            for e in eventos_trecho:
                e.horario_servico_id = antigo.id
            db.add(
                HistoricoMapaServico(
                    horario_servico_id=antigo.id,
                    colaborador_id=colaborador_trecho,
                    cliente_id=horario.cliente_id,
                    tipo_evento="encerrado",
                    dia_semana=antigo.dia_semana,
                    turno=antigo.turno,
                    hora_inicio=antigo.hora_inicio,
                    hora_fim=antigo.hora_fim,
                    motivo=MOTIVO,
                    registrado_por_id=evento.registrado_por_id,
                    criado_em=evento.criado_em,
                )
            )
            # o "editado" vira o inicio do trecho do colaborador novo
            evento.tipo_evento = "iniciado"
            evento.motivo = MOTIVO

            print(
                f"  horario {horario.id} (cliente {horario.cliente_id}, {antigo.dia_semana}/{antigo.turno}): "
                f"colaborador {colaborador_trecho} {inicio_trecho} -> {data_troca}, depois colaborador {evento.colaborador_id}"
            )
            trocas += 1
            inicio_trecho = data_troca
            colaborador_trecho = evento.colaborador_id
            eventos_trecho = []

        eventos_trecho.append(evento)
        ultimo_estado = evento

    if trocas:
        horario.data_inicio = inicio_trecho
    return trocas


def main():
    simular = "--simular" in sys.argv
    db = SessionLocal()
    try:
        ids_com_troca = sorted(
            horario_id
            for (horario_id,) in db.query(HistoricoMapaServico.horario_servico_id)
            .group_by(HistoricoMapaServico.horario_servico_id)
            .having(func.count(func.distinct(HistoricoMapaServico.colaborador_id)) > 1)
            .all()
        )
        total = 0
        for horario_id in ids_com_troca:
            eventos = (
                db.query(HistoricoMapaServico)
                .filter_by(horario_servico_id=horario_id)
                .order_by(HistoricoMapaServico.criado_em.asc(), HistoricoMapaServico.id.asc())
                .all()
            )
            if len({e.colaborador_id for e in eventos}) < 2:
                continue
            horario = db.get(HorarioServico, horario_id)
            if horario is None:
                continue
            total += reconstruir(db, horario, eventos)

        if simular:
            db.rollback()
            print(f"SIMULACAO: {total} troca(s) seriam reconstruidas. Nada foi gravado.")
        else:
            db.commit()
            print(f"{total} troca(s) reconstruidas no historico.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
