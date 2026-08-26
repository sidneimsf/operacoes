"""
Adiciona as colunas de dia/mes de aniversario a tabela colaboradores
(sem apagar dados) e carrega os 85 aniversarios que conseguimos casar
com seguranca contra a planilha de aniversarios (arquivo
dados_aniversarios.json, ao lado deste script).

O "aniversario de empresa" (tempo de casa) nao precisa de carga nenhuma
aqui - ele e calculado direto a partir da data_admissao que ja existe.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_aniversarios.py
"""

import json

from sqlalchemy import text

from database import SessionLocal, engine
from models import Colaborador, Empresa

COMANDOS_ALTER = [
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS aniversario_dia INTEGER",
    "ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS aniversario_mes INTEGER",
]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS_ALTER:
            conn.execute(text(comando))
            print("executado:", comando)

    with open("dados_aniversarios.json", encoding="utf-8") as f:
        aniversarios = json.load(f)

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}
        total_atualizados = 0
        total_nao_encontrados = 0

        for item in aniversarios:
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

            colaborador.aniversario_dia = item["dia"]
            colaborador.aniversario_mes = item["mes"]
            total_atualizados += 1

        db.commit()
        print("")
        print("Colaboradores atualizados com aniversario:", total_atualizados)
        print("Colaboradores nao encontrados:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
