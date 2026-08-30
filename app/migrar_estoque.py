"""
Cria as tabelas de estoque (itens + movimentacoes) e carrega os 37
itens da planilha de controle de EPI (arquivo dados_estoque.json, ao
lado deste script), com a quantidade atual de cada um.

Idempotente: pode rodar mais de uma vez sem duplicar itens (se o item
ja existir para aquela empresa+peca+tamanho, so atualiza a
quantidade).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_estoque.py
"""

import json

import models
from database import SessionLocal, engine
from models import Empresa, EstoqueItem


def main():
    models.EstoqueItem.__table__.create(engine, checkfirst=True)
    models.EstoqueMovimento.__table__.create(engine, checkfirst=True)
    print("Tabelas de estoque OK (criadas ou ja existentes)")

    with open("dados_estoque.json", encoding="utf-8") as f:
        itens = json.load(f)

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}
        total_criados = 0
        total_atualizados = 0
        total_nao_encontrados = 0

        for item in itens:
            empresa_id = empresas_por_nome.get(item["empresa"])
            if empresa_id is None:
                total_nao_encontrados += 1
                continue

            existente = (
                db.query(EstoqueItem)
                .filter_by(empresa_id=empresa_id, tipo_peca=item["tipo_peca"], tamanho=item["tamanho"])
                .first()
            )
            if existente is not None:
                existente.quantidade_atual = item["quantidade"]
                total_atualizados += 1
            else:
                db.add(
                    EstoqueItem(
                        empresa_id=empresa_id,
                        tipo_peca=item["tipo_peca"],
                        tamanho=item["tamanho"],
                        quantidade_atual=item["quantidade"],
                    )
                )
                total_criados += 1

        db.commit()
        print("")
        print("Itens de estoque criados:", total_criados)
        print("Itens ja existentes (quantidade atualizada):", total_atualizados)
        print("Empresas nao encontradas:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
