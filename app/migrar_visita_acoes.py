"""
Adiciona a coluna acoes na tabela visitas_supervisao - registra o que
foi feito em relacao a visita, que pode ser preenchido na hora ou
depois, editando o registro.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_visita_acoes.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE visitas_supervisao ADD COLUMN IF NOT EXISTS acoes VARCHAR(1500)"))
        print("executado: coluna acoes adicionada em visitas_supervisao")


if __name__ == "__main__":
    main()
