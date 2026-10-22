"""
Adiciona as colunas latitude, longitude e geo_precisao na tabela
clientes - usadas pelo Mapa de Clientes para colocar o pino de cada
cliente.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_clientes_localizacao.py
Depois, para localizar os clientes que ja existem:
    docker compose exec app python geocodificar_clientes.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS geo_precisao VARCHAR(20)"))
        print("executado: colunas latitude, longitude e geo_precisao adicionadas em clientes")


if __name__ == "__main__":
    main()
