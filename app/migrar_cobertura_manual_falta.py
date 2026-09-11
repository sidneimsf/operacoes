"""
Adiciona a coluna colaborador_relacionado_nome_manual na tabela
colaborador_eventos - permite digitar o nome de quem cobriu uma falta
quando essa pessoa nao e um colaborador cadastrado no sistema
(freelancer/terceirizado).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_cobertura_manual_falta.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE colaborador_eventos ADD COLUMN IF NOT EXISTS colaborador_relacionado_nome_manual VARCHAR(150)"
        ))
        print("executado: coluna colaborador_relacionado_nome_manual adicionada em colaborador_eventos")


if __name__ == "__main__":
    main()
