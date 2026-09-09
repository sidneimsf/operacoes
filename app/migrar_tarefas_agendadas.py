"""
Cria a tabela tarefas_agendadas - o agendador de tarefas (calendario de
lembretes) do sistema.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_tarefas_agendadas.py
"""

import models
from database import engine


def main():
    models.TarefaAgendada.__table__.create(engine, checkfirst=True)
    print("Tabela tarefas_agendadas OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
