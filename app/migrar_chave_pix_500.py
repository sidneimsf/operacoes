"""
Aumenta a coluna chave_pix de VARCHAR(150) para VARCHAR(500) nas
tabelas custos_diarios e freelancers. O "PIX copia e cola" (codigo do
QR Code) passa facil de 150 caracteres, e o lancamento do custo dava
erro ao salvar.

Seguro de rodar: so aumenta o tamanho da coluna, nao apaga nem altera
nenhum dado que ja existe. Pode rodar mais de uma vez.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_chave_pix_500.py
"""

from sqlalchemy import text

from database import engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE custos_diarios ALTER COLUMN chave_pix TYPE VARCHAR(500)"))
        conn.execute(text("ALTER TABLE freelancers ALTER COLUMN chave_pix TYPE VARCHAR(500)"))
        print("executado: chave_pix agora aceita ate 500 caracteres em custos_diarios e freelancers")


if __name__ == "__main__":
    main()
