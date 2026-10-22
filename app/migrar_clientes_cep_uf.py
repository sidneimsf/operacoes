"""
Adiciona as colunas uf e cep na tabela clientes - completam o endereco
e deixam a localizacao no Mapa de Clientes bem mais precisa (sem UF,
"Centro, Sao Jose" podia cair em outro estado).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_clientes_cep_uf.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS uf VARCHAR(2)"))
        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS cep VARCHAR(10)"))
        print("executado: colunas uf e cep adicionadas em clientes")


if __name__ == "__main__":
    main()
