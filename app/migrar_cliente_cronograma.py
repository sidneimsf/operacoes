"""
Cria a tabela cliente_cronogramas, usada pra guardar o cronograma de
atividades de cada cliente (digitado no sistema ou como arquivo
anexado, PDF/Excel).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_cliente_cronograma.py
"""

import models
from database import engine


def main():
    models.ClienteCronograma.__table__.create(engine, checkfirst=True)
    print("Tabela cliente_cronogramas OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
