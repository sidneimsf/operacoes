"""
Adiciona a coluna visitas_comerciais_vistas_em na tabela usuarios - usada
pro balao vermelho no menu Visita Comercial quando um supervisor cadastra
uma visita nova (so pra quem recebe esse alerta).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_visitas_comerciais_vistas.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS visitas_comerciais_vistas_em TIMESTAMPTZ"))
        print("executado: coluna visitas_comerciais_vistas_em adicionada em usuarios")


if __name__ == "__main__":
    main()
