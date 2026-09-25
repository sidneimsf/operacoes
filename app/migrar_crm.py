"""
Cria as tabelas do modulo CRM: cliente_contratos (valor, vigencia e
reajuste do contrato), cliente_contatos (varios contatos por cliente) e
pesquisas_satisfacao (notas NPS 0-10).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_crm.py
"""

import models
from database import engine


def main():
    models.ClienteContrato.__table__.create(engine, checkfirst=True)
    print("Tabela cliente_contratos OK (criada ou ja existente)")
    models.ClienteContato.__table__.create(engine, checkfirst=True)
    print("Tabela cliente_contatos OK (criada ou ja existente)")
    models.PesquisaSatisfacao.__table__.create(engine, checkfirst=True)
    print("Tabela pesquisas_satisfacao OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
