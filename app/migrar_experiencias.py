"""
Adiciona as colunas de fim de periodo de experiencia (30 e 90 dias) na
tabela colaboradores, e carrega os 20 colaboradores que conseguimos
casar com seguranca contra a planilha de experiencias (arquivo
dados_experiencias.json, ao lado deste script).

Para colaboradores futuros (criados depois desta migracao), os dois
checkpoints sao calculados automaticamente a partir da data de
admissao (30 = admissao + 29 dias, 90 = admissao + 89 dias) - nao
precisa rodar nada manualmente para eles.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_experiencias.py
"""

import json
from datetime import date

from sqlalchemy import text

from database import SessionLocal, engine
from models import Colaborador, Empresa

COMANDOS_ALTER = [
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS data_fim_experiencia_30 DATE",
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS data_fim_experiencia_90 DATE",
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS_ALTER:
            conn.execute(text(comando))
            print("executado:", comando)

    with open("dados_experiencias.json", encoding="utf-8") as f:
        experiencias = json.load(f)

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}
        total_atualizados = 0
        total_nao_encontrados = 0

        for item in experiencias:
            empresa_id = empresas_por_nome.get(item["empresa_colaborador"])
            if empresa_id is None:
                continue

            colaborador = (
                db.query(Colaborador)
                .filter_by(empresa_id=empresa_id, nome=item["colaborador_nome"])
                .first()
            )
            if colaborador is None:
                total_nao_encontrados += 1
                print("colaborador nao encontrado (pulando):", item["colaborador_nome"])
                continue

            colaborador.data_fim_experiencia_30 = date.fromisoformat(item["data_fim_experiencia_30"])
            colaborador.data_fim_experiencia_90 = date.fromisoformat(item["data_fim_experiencia_90"])
            total_atualizados += 1

        db.commit()
        print("")
        print("Colaboradores atualizados com periodo de experiencia:", total_atualizados)
        print("Colaboradores nao encontrados:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
