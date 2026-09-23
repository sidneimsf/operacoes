"""
Suporte a exclusao de avisos com opcao de desfazer por 1 hora:
- coluna `excluido_em` em avisos (exclusao feita pelo autor, some pra todos)
- tabela `avisos_exclusoes` (exclusao feita por quem recebeu, so do proprio mural)

Nao apaga dados. Idempotente.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_exclusao_avisos.py
"""

from sqlalchemy import text

from database import engine

COMANDOS = [
    "ALTER TABLE avisos ADD COLUMN IF NOT EXISTS excluido_em TIMESTAMPTZ",
    """
    CREATE TABLE IF NOT EXISTS avisos_exclusoes (
        id SERIAL PRIMARY KEY,
        aviso_id INTEGER NOT NULL REFERENCES avisos(id) ON DELETE CASCADE,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
        excluido_em TIMESTAMPTZ NOT NULL,
        CONSTRAINT uq_aviso_exclusao_usuario UNIQUE (aviso_id, usuario_id)
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
