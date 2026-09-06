"""
Adiciona razao_social e cnpj na tabela empresas, e ja preenche com os
dados reais das 4 empresas do grupo.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_empresa_razao_social.py
"""

from sqlalchemy import text

from database import SessionLocal, engine
from models import Empresa

DADOS_EMPRESAS = {
    "CORDSUL": {"razao_social": "Cordsul Serviços Especializados Ltda", "cnpj": "20.818.006/0001-88"},
    "KRETZER": {"razao_social": "Cordero Serviços Especializados Ltda", "cnpj": "33.366.648/0001-35"},
    "STAR SUL": {"razao_social": "Starsul Serviços Especializados Ltda", "cnpj": "49.449.723/0001-61"},
    "FLC": {"razao_social": "FLC Serviços Especializados Ltda", "cnpj": "64.825.918/0001-52"},
}


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS razao_social VARCHAR(200)"))
        conn.execute(text("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cnpj VARCHAR(20)"))
        print("executado: colunas razao_social e cnpj adicionadas em empresas")

    db = SessionLocal()
    try:
        for nome, dados in DADOS_EMPRESAS.items():
            empresa = db.query(Empresa).filter_by(nome=nome).first()
            if empresa is None:
                print(f"aviso: empresa '{nome}' nao encontrada, pulando")
                continue
            empresa.razao_social = dados["razao_social"]
            empresa.cnpj = dados["cnpj"]
            print(f"{nome}: {dados['razao_social']} - {dados['cnpj']}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
