"""
Cria as tabelas movimentacao_meses e movimentacao_linhas - a movimentacao
de cobranca mensal do menu Gerencia (antes era a planilha
"MOVIMENTACAO <MES> <ANO>.xlsx") - e a coluna nota_ok (nota emitida),
que veio depois.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_movimentacao.py
"""

from sqlalchemy import text

import models
from database import engine


def main():
    models.MovimentacaoMes.__table__.create(engine, checkfirst=True)
    models.MovimentacaoLinha.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE movimentacao_linhas ADD COLUMN IF NOT EXISTS nota_ok BOOLEAN NOT NULL DEFAULT FALSE"))
    print("Tabelas movimentacao_meses e movimentacao_linhas OK (criadas ou ja existentes, com nota_ok)")


if __name__ == "__main__":
    main()
