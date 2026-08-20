"""
Adiciona a coluna `prioridade` a tabela chamados (sem apagar dados) e
garante que a tabela `avisos` exista. Idempotente.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_prioridade_e_avisos.py
"""

from sqlalchemy import text

import models
from database import engine

COMANDOS = [
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS prioridade VARCHAR(20) DEFAULT 'normal'",
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS:
            conn.execute(text(comando))
            print("executado:", comando)

    # cria a tabela avisos se ainda nao existir (nao mexe em tabelas ja existentes)
    models.Aviso.__table__.create(engine, checkfirst=True)
    print("tabela avisos: OK (criada ou ja existente)")

    print("")
    print("Migracao concluida. Nenhum dado foi apagado.")


if __name__ == "__main__":
    main()
