"""
Cria a tabela freelancers (cadastro leve de nome + PIX pra quem cobre
diarias sem ser colaborador da empresa) e adiciona a coluna
freelancer_id em custos_diarios.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_freelancers.py
"""

from sqlalchemy import text

import models
from database import engine


def main():
    models.Freelancer.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE custos_diarios ADD COLUMN IF NOT EXISTS freelancer_id INTEGER REFERENCES freelancers(id)"))
    print("executado: tabela freelancers criada e coluna freelancer_id adicionada em custos_diarios")


if __name__ == "__main__":
    main()
