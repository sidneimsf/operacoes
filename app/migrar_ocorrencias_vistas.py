"""
Adiciona a coluna ocorrencias_vistas_em na tabela usuarios - usada pro
balao vermelho de notificacao quando um chamado novo aparece ou muda
de status.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_ocorrencias_vistas.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ocorrencias_vistas_em TIMESTAMPTZ"))
        print("executado: coluna ocorrencias_vistas_em adicionada em usuarios")


if __name__ == "__main__":
    main()
