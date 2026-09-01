"""
Adiciona a coluna de data de desligamento na tabela colaboradores.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_data_desligamento.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS data_desligamento DATE"))
        print("executado: ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS data_desligamento")


if __name__ == "__main__":
    main()
