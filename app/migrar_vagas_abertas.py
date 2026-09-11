"""
Cria a tabela vagas_abertas - o mural de "Vagas Abertas".

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_vagas_abertas.py
"""

import models
from database import engine


def main():
    models.VagaAberta.__table__.create(engine, checkfirst=True)
    print("Tabela vagas_abertas OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
