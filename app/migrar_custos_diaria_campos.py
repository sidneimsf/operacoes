"""
Adiciona as colunas novas em custos_diarios, usadas quando o tipo e
"diaria": colaborador_id (quem estava faltando/o posto), status_diaria
(motivo), cliente_id (onde), cobertura_colaborador_id (quem foi cobrir).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_custos_diaria_campos.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE custos_diarios ADD COLUMN IF NOT EXISTS colaborador_id INTEGER REFERENCES colaboradores(id)"))
        conn.execute(text("ALTER TABLE custos_diarios ADD COLUMN IF NOT EXISTS status_diaria VARCHAR(30)"))
        conn.execute(text("ALTER TABLE custos_diarios ADD COLUMN IF NOT EXISTS cliente_id INTEGER REFERENCES clientes(id)"))
        conn.execute(text("ALTER TABLE custos_diarios ADD COLUMN IF NOT EXISTS cobertura_colaborador_id INTEGER REFERENCES colaboradores(id)"))
        print("executado: colunas de diaria adicionadas em custos_diarios")


if __name__ == "__main__":
    main()
