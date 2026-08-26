"""
Adiciona as colunas de senha/chave de acesso a tabela clientes (sem
apagar dados) e carrega os 152 registros que conseguimos casar com
seguranca contra a planilha de controle de acessos (arquivo
dados_acessos.json, ao lado deste script).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_acessos_clientes.py
"""

import json

from sqlalchemy import text

from database import SessionLocal, engine
from models import Cliente, Empresa

COMANDOS_ALTER = [
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS senha_acesso VARCHAR(200)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS chave_acesso VARCHAR(200)",
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS_ALTER:
            conn.execute(text(comando))
            print("executado:", comando)

    with open("dados_acessos.json", encoding="utf-8") as f:
        acessos = json.load(f)

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}
        total_atualizados = 0
        total_nao_encontrados = 0

        for item in acessos:
            empresa_id = empresas_por_nome.get(item["empresa_cliente"])
            if empresa_id is None:
                continue

            cliente = (
                db.query(Cliente)
                .filter_by(empresa_id=empresa_id, nome=item["cliente_nome"])
                .first()
            )
            if cliente is None:
                total_nao_encontrados += 1
                print("cliente nao encontrado (pulando):", item["empresa_cliente"], "-", item["cliente_nome"])
                continue

            cliente.senha_acesso = item["senha"]
            cliente.chave_acesso = item["chave"]
            total_atualizados += 1

        db.commit()
        print("")
        print("Clientes atualizados com dados de acesso:", total_atualizados)
        print("Clientes nao encontrados:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
