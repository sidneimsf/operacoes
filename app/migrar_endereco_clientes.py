"""
Adiciona as colunas de endereco/contato a tabela clientes (sem apagar
dados) e carrega o endereco/responsavel/telefone dos clientes que
conseguimos casar com seguranca contra a planilha de cadastro (arquivo
dados_enderecos.json, que fica ao lado deste script).

Os clientes tipo "Posto Galo"/"Posto Ale" foram deixados de fora de
proposito - sao unidades guarda-chuva que representam varios locais
fisicos diferentes, entao um unico endereco nao faria sentido para
eles. Os outros clientes sem correspondencia clara tambem ficaram de
fora, para nao arriscar vincular endereco errado.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_endereco_clientes.py
"""

import json

from sqlalchemy import text

from database import SessionLocal, engine
from models import Cliente, Empresa

COMANDOS_ALTER = [
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS endereco VARCHAR(300)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS bairro VARCHAR(100)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS cidade VARCHAR(100)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS responsavel_nome VARCHAR(150)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS responsavel_telefone VARCHAR(50)",
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS_ALTER:
            conn.execute(text(comando))
            print("executado:", comando)

    with open("dados_enderecos.json", encoding="utf-8") as f:
        enderecos = json.load(f)

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}
        total_atualizados = 0
        total_nao_encontrados = 0

        for item in enderecos:
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

            cliente.endereco = item["endereco"]
            cliente.bairro = item["bairro"]
            cliente.cidade = item["cidade"]
            cliente.responsavel_nome = item["responsavel"]
            cliente.responsavel_telefone = item["telefone"]
            total_atualizados += 1

        db.commit()
        print("")
        print("Enderecos atualizados:", total_atualizados)
        print("Clientes nao encontrados:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
