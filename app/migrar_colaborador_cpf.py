"""
Adiciona a coluna cpf na tabela colaboradores - guardada so com os 11
digitos (sem pontos e traco); a tela formata na exibicao.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_colaborador_cpf.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS cpf VARCHAR(11)"))
        print("executado: coluna cpf adicionada em colaboradores")


if __name__ == "__main__":
    main()
