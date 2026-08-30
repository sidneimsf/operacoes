"""
Adiciona a coluna de supervisor responsavel a tabela clientes.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_cliente_supervisor.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS supervisor_id INTEGER REFERENCES usuarios(id)"))
        print("executado: ALTER TABLE clientes ADD COLUMN IF NOT EXISTS supervisor_id")


if __name__ == "__main__":
    main()
