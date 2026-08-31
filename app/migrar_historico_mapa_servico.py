"""
Adiciona data_inicio/data_fim na tabela horarios_servico (base para o
historico), e cria a tabela historico_mapa_servico (log de auditoria).

Os vinculos que ja existem hoje recebem data_inicio = a data em que
esta migracao for rodada (nao existe registro de quando cada um
comecou de verdade) e data_fim em branco (continuam ativos).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_historico_mapa_servico.py
"""

from sqlalchemy import text

import models
from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE horarios_servico ADD COLUMN IF NOT EXISTS data_inicio DATE"))
        conn.execute(text("ALTER TABLE horarios_servico ADD COLUMN IF NOT EXISTS data_fim DATE"))
        print("executado: colunas data_inicio/data_fim adicionadas")

        # Essa tabela nunca teve uma data de criacao registrada, entao nao ha
        # como saber quando cada vinculo comecou de verdade. Para os
        # registros que ja existiam antes desta migracao, usamos a data de
        # hoje como marco zero - e o melhor que da pra fazer com honestidade.
        resultado = conn.execute(
            text("UPDATE horarios_servico SET data_inicio = CURRENT_DATE WHERE data_inicio IS NULL")
        )
        print(f"registros existentes com data_inicio marcada como hoje (marco zero): {resultado.rowcount}")

        conn.execute(text("ALTER TABLE horarios_servico ALTER COLUMN data_inicio SET NOT NULL"))
        print("executado: data_inicio agora e obrigatoria pra novos registros")

    models.HistoricoMapaServico.__table__.create(engine, checkfirst=True)
    print("Tabela historico_mapa_servico OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
