"""
Adiciona as colunas de arquivo anexado a acao corretiva, na tabela
chamados.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_acao_corretiva_arquivo.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS acao_corretiva_arquivo_path VARCHAR(300)"))
        conn.execute(text("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS acao_corretiva_arquivo_nome_original VARCHAR(200)"))
        print("executado: colunas de arquivo da acao corretiva adicionadas em chamados")


if __name__ == "__main__":
    main()
