"""
Cria as tabelas visitas_comerciais e visitas_comerciais_anexos - registro
de visitas a locais que ainda nao sao clientes (prospeccao ou orcamento
aprovado pelo escritorio), com funil de status e fotos/documentos.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_visitas_comerciais.py
"""

import models
from database import engine


def main():
    models.VisitaComercial.__table__.create(engine, checkfirst=True)
    print("Tabela visitas_comerciais OK (criada ou ja existente)")
    models.VisitaComercialAnexo.__table__.create(engine, checkfirst=True)
    print("Tabela visitas_comerciais_anexos OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
