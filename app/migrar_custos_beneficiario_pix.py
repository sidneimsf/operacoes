"""
Adiciona as colunas nome_beneficiario e chave_pix na tabela
custos_diarios. Essas colunas ja eram usadas pelo sistema ha tempos,
mas por algum motivo nao existiam de fato na tabela em producao -
causando erro ao lancar qualquer custo novo.

Seguro de rodar: usa ADD COLUMN IF NOT EXISTS, entao nao apaga nem
altera nenhum dado que ja existe.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_custos_beneficiario_pix.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE custos_diarios ADD COLUMN IF NOT EXISTS nome_beneficiario VARCHAR(150)"))
        conn.execute(text("ALTER TABLE custos_diarios ADD COLUMN IF NOT EXISTS chave_pix VARCHAR(150)"))
        print("executado: colunas nome_beneficiario e chave_pix adicionadas em custos_diarios")


if __name__ == "__main__":
    main()
