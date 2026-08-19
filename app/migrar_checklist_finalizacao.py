"""
Adiciona as colunas do checklist de finalizacao (e, por seguranca,
tambem a coluna responsavel_id, caso a etapa anterior nao tenha sido
aplicada ainda) a tabela `chamados` ja existente, sem apagar nenhum
dado. Idempotente: pode rodar mais de uma vez sem erro (usa ADD COLUMN
IF NOT EXISTS em tudo).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_checklist_finalizacao.py
"""

from sqlalchemy import text

from database import engine

COMANDOS = [
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS responsavel_id INTEGER",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS finalizado_em TIMESTAMPTZ",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS finalizado_por_id INTEGER",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS confirmacao_vista BOOLEAN DEFAULT FALSE",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS fechamento_pendencia BOOLEAN",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS fechamento_pendencia_detalhe VARCHAR(500)",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS fechamento_documento_enviado BOOLEAN",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS fechamento_documento_detalhe VARCHAR(500)",
    "ALTER TABLE chamados ADD COLUMN IF NOT EXISTS fechamento_observacoes VARCHAR(1000)",
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
