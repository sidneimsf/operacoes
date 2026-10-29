"""
Cria as tabelas movimentacao_meses e movimentacao_linhas - a movimentacao
de cobranca mensal do menu Gerencia (antes era a planilha
"MOVIMENTACAO <MES> <ANO>.xlsx").

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_movimentacao.py
"""

import models
from database import engine


def main():
    models.MovimentacaoMes.__table__.create(engine, checkfirst=True)
    models.MovimentacaoLinha.__table__.create(engine, checkfirst=True)
    print("Tabelas movimentacao_meses e movimentacao_linhas OK (criadas ou ja existentes)")


if __name__ == "__main__":
    main()
