"""
Adiciona as colunas de VT (vale transporte) e seguro de vida na tabela
colaboradores, cria a tabela de lancamentos do METLIFE, e carrega os
3 conjuntos de dados que conseguimos casar com seguranca (arquivos
dados_vt_finais.json, dados_seguro_vida_finais.json e
dados_metlife_finais.json, ao lado deste script).

Cartoes VT e seguros de quem nao esta mais na empresa (ou nao foi
encontrado com seguranca) ficaram de fora de proposito.

Idempotente: pode rodar mais de uma vez sem duplicar nada de METLIFE
(por colaborador+dependente), e sem sobrescrever VT/seguro com dados
antigos se ja tiver sido editado manualmente depois.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_beneficios.py
"""

import json
from datetime import date

from sqlalchemy import text

import models
from database import SessionLocal, engine
from models import Colaborador, Empresa, MetlifeLancamento

COMANDOS_ALTER = [
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS vt_numero_cartao VARCHAR(50)",
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS vt_situacao VARCHAR(50)",
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS vt_saldo FLOAT",
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS seguro_vida_data_inclusao DATE",
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS seguro_vida_data_exclusao DATE",
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS_ALTER:
            conn.execute(text(comando))
            print("executado:", comando)

    models.MetlifeLancamento.__table__.create(engine, checkfirst=True)
    print("Tabela metlife_lancamentos OK (criada ou ja existente)")

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}

        # ---------- VT ----------
        with open("dados_vt_finais.json", encoding="utf-8") as f:
            vt_dados = json.load(f)
        total_vt = 0
        for item in vt_dados:
            empresa_id = empresas_por_nome.get(item["empresa_colaborador"])
            if empresa_id is None:
                continue
            colaborador = db.query(Colaborador).filter_by(empresa_id=empresa_id, nome=item["colaborador_nome"]).first()
            if colaborador is None:
                continue
            colaborador.vt_numero_cartao = item["cartao"]
            colaborador.vt_situacao = item["situacao"]
            colaborador.vt_saldo = item["saldo"]
            total_vt += 1
        print("Colaboradores atualizados com VT:", total_vt)

        # ---------- Seguro de vida ----------
        with open("dados_seguro_vida_finais.json", encoding="utf-8") as f:
            seguro_dados = json.load(f)
        total_seguro = 0
        for item in seguro_dados:
            empresa_id = empresas_por_nome.get(item["empresa_colaborador"])
            if empresa_id is None:
                continue
            colaborador = db.query(Colaborador).filter_by(empresa_id=empresa_id, nome=item["colaborador_nome"]).first()
            if colaborador is None:
                continue
            colaborador.seguro_vida_data_inclusao = (
                date.fromisoformat(item["data_inclusao"]) if item["data_inclusao"] else None
            )
            colaborador.seguro_vida_data_exclusao = (
                date.fromisoformat(item["data_exclusao"]) if item["data_exclusao"] else None
            )
            total_seguro += 1
        print("Colaboradores atualizados com seguro de vida:", total_seguro)

        db.commit()

        # ---------- METLIFE ----------
        with open("dados_metlife_finais.json", encoding="utf-8") as f:
            metlife_dados = json.load(f)
        total_metlife = 0
        total_metlife_pulados = 0
        for item in metlife_dados:
            empresa_id = empresas_por_nome.get(item["empresa_colaborador"])
            if empresa_id is None:
                continue
            colaborador = db.query(Colaborador).filter_by(empresa_id=empresa_id, nome=item["colaborador_nome"]).first()
            if colaborador is None:
                continue

            ja_existe = (
                db.query(MetlifeLancamento)
                .filter_by(colaborador_id=colaborador.id, nome_dependente=item["nome_dependente"])
                .first()
            )
            if ja_existe is not None:
                total_metlife_pulados += 1
                continue

            db.add(
                MetlifeLancamento(
                    colaborador_id=colaborador.id,
                    nome_dependente=item["nome_dependente"],
                    valor=item["valor"],
                    desconta=item["desconta"],
                    data_inclusao=date.fromisoformat(item["data_inclusao"]) if item["data_inclusao"] else None,
                    data_exclusao=date.fromisoformat(item["data_exclusao"]) if item["data_exclusao"] else None,
                )
            )
            total_metlife += 1

        db.commit()
        print("Lancamentos METLIFE criados:", total_metlife)
        print("Lancamentos METLIFE ja existentes (pulados):", total_metlife_pulados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
