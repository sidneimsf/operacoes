"""
Cria a tabela visitas_supervisao - registro de visitas presenciais que
supervisores fazem aos clientes (data, com quem falou, observacoes).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_visitas_supervisao.py
"""

import models
from database import engine


def main():
    models.VisitaSupervisao.__table__.create(engine, checkfirst=True)
    print("Tabela visitas_supervisao OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
