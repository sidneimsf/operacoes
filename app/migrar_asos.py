"""
Carrega os 83 ASOs (exames ocupacionais) que conseguimos casar com
seguranca contra a planilha de RH, criando um evento tipo 'aso' na
linha do tempo de cada colaborador (arquivo dados_asos.json, ao lado
deste script).

Idempotente: se o colaborador ja tiver um evento de ASO com a mesma
data de vencimento, pula sem duplicar.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_asos.py
"""

import json
from datetime import date

from database import SessionLocal
from models import Colaborador, ColaboradorEvento, Empresa, Usuario


def main():
    with open("dados_asos.json", encoding="utf-8") as f:
        asos = json.load(f)

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}

        # usa o primeiro usuario escritorio encontrado como "quem registrou"
        usuario_sistema = db.query(Usuario).filter_by(papel="escritorio").first()
        if usuario_sistema is None:
            print("Nenhum usuario escritorio encontrado - nao da pra registrar os ASOs (precisa de um 'registrado_por').")
            return

        total_criados = 0
        total_pulados = 0
        total_nao_encontrados = 0

        for item in asos:
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

            data_vencimento = date.fromisoformat(item["data_vencimento"])

            ja_existe = (
                db.query(ColaboradorEvento)
                .filter_by(colaborador_id=colaborador.id, tipo="aso", data_fim=data_vencimento)
                .first()
            )
            if ja_existe:
                total_pulados += 1
                continue

            evento = ColaboradorEvento(
                colaborador_id=colaborador.id,
                tipo="aso",
                descricao="Importado da planilha de controle de ASOs",
                data_inicio=date.fromisoformat(item["data_exame"]) if item["data_exame"] else None,
                data_fim=data_vencimento,
                registrado_por_id=usuario_sistema.id,
            )
            db.add(evento)
            total_criados += 1

        db.commit()
        print("")
        print("ASOs criados:", total_criados)
        print("Ja existentes (pulados):", total_pulados)
        print("Colaboradores nao encontrados:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
