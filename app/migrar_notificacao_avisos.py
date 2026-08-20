"""
Adiciona a coluna `avisos_vistos_em` a tabela usuarios (sem apagar
dados). Idempotente.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_notificacao_avisos.py
"""

from sqlalchemy import text

from database import engine

COMANDOS = [
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS avisos_vistos_em TIMESTAMPTZ",
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS:
            conn.execute(text(comando))
            print("executado:", comando)
    print("")
    print("Migracao concluida. Nenhum dado foi apagado.")


if __name__ == "__main__":
    main()
