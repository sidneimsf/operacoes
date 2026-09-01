"""
Apaga lancamentos especificos da linha do tempo dos colaboradores,
pelo ID. Use isso depois de rodar listar_lancamentos_colaboradores.py
e decidir quais IDs sao de teste.

Mostra um resumo do que vai ser apagado ANTES de apagar de verdade, e
pede confirmacao digitada. Se o lancamento tiver um arquivo anexado
(documento, atestado, etc.), o arquivo tambem e removido do disco.

COMO USAR
---------
Edite a lista IDS_PARA_APAGAR abaixo com os numeros que voce quer
remover, depois rode na VPS, dentro do container da aplicacao:
    docker compose exec app python apagar_lancamentos_colaboradores.py
"""

import os

from database import SessionLocal
from models import ColaboradorEvento

# -----------------------------------------------------------------
# EDITE AQUI: coloque os IDs dos lancamentos de teste que quer apagar
# -----------------------------------------------------------------
IDS_PARA_APAGAR = [
    # 1, 2, 3,
]


def main():
    if not IDS_PARA_APAGAR:
        print("Nenhum ID informado. Edite a lista IDS_PARA_APAGAR no topo deste arquivo antes de rodar.")
        return

    db = SessionLocal()
    try:
        eventos = db.query(ColaboradorEvento).filter(ColaboradorEvento.id.in_(IDS_PARA_APAGAR)).all()

        if not eventos:
            print("Nenhum lancamento encontrado com esses IDs.")
            return

        print(f"Os {len(eventos)} lancamentos abaixo serao apagados PERMANENTEMENTE:\n")
        for e in eventos:
            descricao = (e.descricao or "").replace("\n", " ")[:40]
            print(
                f"id={e.id:4d} | {e.criado_em.strftime('%d/%m/%Y %H:%M')} | "
                f"colaborador={e.colaborador.nome[:25]:25s} | tipo={e.tipo:12s} | "
                f"descricao={descricao}"
            )

        encontrados_ids = {e.id for e in eventos}
        nao_encontrados = set(IDS_PARA_APAGAR) - encontrados_ids
        if nao_encontrados:
            print(f"\n(IDs que voce informou mas nao existem, ignorados: {sorted(nao_encontrados)})")

        resposta = input("\nDigite APAGAR para confirmar, ou qualquer outra coisa para cancelar: ")
        if resposta.strip() != "APAGAR":
            print("Cancelado. Nada foi apagado.")
            return

        for e in eventos:
            if e.arquivo_path and os.path.exists(e.arquivo_path):
                os.remove(e.arquivo_path)
            db.delete(e)
        db.commit()
        print(f"\n{len(eventos)} lancamento(s) apagado(s) com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
