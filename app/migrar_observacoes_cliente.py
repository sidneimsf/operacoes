"""
Adiciona a coluna observacoes na tabela clientes - pra particularidades
como "Chave fica dentro da zeladoria".

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_observacoes_cliente.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS observacoes VARCHAR(1000)"))
        print("executado: coluna observacoes adicionada em clientes")


if __name__ == "__main__":
    main()
