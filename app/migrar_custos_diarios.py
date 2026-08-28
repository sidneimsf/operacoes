"""
Cria a tabela de custos diarios (reembolso de despesas dos supervisores).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_custos_diarios.py
"""

import models
from database import engine


def main():
    models.CustoDiario.__table__.create(engine, checkfirst=True)
    print("Tabela custos_diarios OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
