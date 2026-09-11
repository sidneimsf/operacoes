"""
Adiciona a coluna entregue_para_nome_manual na tabela
estoque_movimentos - permite digitar o nome de quem recebeu um item
quando essa pessoa nao e um colaborador cadastrado no sistema.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_estoque_entregue_manual.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE estoque_movimentos ADD COLUMN IF NOT EXISTS entregue_para_nome_manual VARCHAR(150)"
        ))
        print("executado: coluna entregue_para_nome_manual adicionada em estoque_movimentos")


if __name__ == "__main__":
    main()
