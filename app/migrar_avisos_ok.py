"""
Cria a tabela avisos_ok - o "Ok" que quem recebeu um aviso da pra avisar
o autor que o assunto ja foi visto/resolvido.

Nao apaga dados. Idempotente.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_avisos_ok.py
"""

from sqlalchemy import text

from database import engine

COMANDOS = [
    """
    CREATE TABLE IF NOT EXISTS avisos_ok (
        id SERIAL PRIMARY KEY,
        aviso_id INTEGER NOT NULL REFERENCES avisos(id) ON DELETE CASCADE,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
        ok_em TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_aviso_ok_usuario UNIQUE (aviso_id, usuario_id)
    )
    """,
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS:
            conn.execute(text(comando))
            print("executado:", " ".join(comando.split()))
    print("")
    print("Migracao concluida. Nenhum dado foi apagado.")


if __name__ == "__main__":
    main()
