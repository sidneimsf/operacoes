"""
Adiciona a coluna horas na tabela colaborador_eventos - usada pelo tipo
de registro "Horas falta" (falta parcial: quantas horas o colaborador
faltou num dia).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_evento_horas.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE colaborador_eventos ADD COLUMN IF NOT EXISTS horas DOUBLE PRECISION"))
        print("executado: coluna horas adicionada em colaborador_eventos")


if __name__ == "__main__":
    main()
