"""
Cadastra os 29 postos da rede Posto Galo como clientes individuais,
com endereco, bairro, cidade, responsavel no local, telefone e o
supervisor responsavel (arquivo dados_postos_galo.json, ao lado deste
script).

Isso NAO mexe no cliente guarda-chuva "POSTO GALO LTDA" que ja possa
existir (usado por chamados/horarios antigos) - e so um cadastro novo,
com cada posto separado.

Idempotente: se um posto com aquele nome ja existir para a empresa,
pula sem duplicar.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_postos_galo.py
"""

import json

from database import SessionLocal
from models import Cliente, Empresa, Usuario

MAPA_EMPRESA = {"Star Sul": "STAR SUL", "FLC": "FLC"}


def main():
    with open("dados_postos_galo.json", encoding="utf-8") as f:
        postos = json.load(f)

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}
        supervisores_por_nome = {u.nome: u.id for u in db.query(Usuario).filter_by(papel="supervisor").all()}

        total_criados = 0
        total_ja_existentes = 0
        total_sem_empresa = 0
        total_sem_supervisor = 0

        for item in postos:
            empresa_nome = MAPA_EMPRESA.get(item["empresa_raw"], item["empresa_raw"].upper())
            empresa_id = empresas_por_nome.get(empresa_nome)
            if empresa_id is None:
                total_sem_empresa += 1
                print("empresa nao encontrada (pulando):", item["empresa_raw"], "-", item["nome"])
                continue

            ja_existe = db.query(Cliente).filter_by(empresa_id=empresa_id, nome=item["nome"]).first()
            if ja_existe is not None:
                total_ja_existentes += 1
                continue

            supervisor_id = None
            if item["supervisor_raw"]:
                supervisor_id = supervisores_por_nome.get(item["supervisor_raw"])
                if supervisor_id is None:
                    total_sem_supervisor += 1
                    print("supervisor nao encontrado:", item["supervisor_raw"], "- posto:", item["nome"])

            cliente = Cliente(
                empresa_id=empresa_id,
                nome=item["nome"],
                responsavel_nome=item["responsavel"],
                responsavel_telefone=item["telefone"],
                endereco=item["endereco"],
                bairro=item["bairro"],
                cidade=item["cidade"],
                supervisor_id=supervisor_id,
            )
            db.add(cliente)
            total_criados += 1

        db.commit()
        print("")
        print("Postos cadastrados:", total_criados)
        print("Ja existentes (pulados):", total_ja_existentes)
        print("Sem empresa correspondente:", total_sem_empresa)
        print("Sem supervisor correspondente (cadastrado sem supervisor):", total_sem_supervisor)
    finally:
        db.close()


if __name__ == "__main__":
    main()
