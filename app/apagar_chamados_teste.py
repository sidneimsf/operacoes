"""
Apaga chamados especificos, pelo ID. Use isso depois de rodar
listar_chamados.py e decidir quais IDs sao de teste.

Mostra um resumo do que vai ser apagado ANTES de apagar de verdade, e
pede confirmacao digitada.

COMO USAR
---------
Edite a lista IDS_PARA_APAGAR abaixo com os numeros que voce quer
remover, depois rode na VPS, dentro do container da aplicacao:
    docker compose exec app python apagar_chamados_teste.py
"""

from database import SessionLocal
from models import Chamado

# -----------------------------------------------------------------
# EDITE AQUI: coloque os IDs dos chamados de teste que quer apagar
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
        chamados = db.query(Chamado).filter(Chamado.id.in_(IDS_PARA_APAGAR)).all()

        if not chamados:
            print("Nenhum chamado encontrado com esses IDs.")
            return

        print(f"Os {len(chamados)} chamados abaixo serao apagados PERMANENTEMENTE:\n")
        for c in chamados:
            print(
                f"id={c.id:4d} | {c.criado_em.strftime('%d/%m/%Y %H:%M')} | "
                f"cliente={c.cliente.nome[:30]:30s} | descricao={c.descricao[:40]}"
            )

        encontrados_ids = {c.id for c in chamados}
        nao_encontrados = set(IDS_PARA_APAGAR) - encontrados_ids
        if nao_encontrados:
            print(f"\n(IDs que voce informou mas nao existem, ignorados: {sorted(nao_encontrados)})")

        resposta = input("\nDigite APAGAR para confirmar, ou qualquer outra coisa para cancelar: ")
        if resposta.strip() != "APAGAR":
            print("Cancelado. Nada foi apagado.")
            return

        for c in chamados:
            db.delete(c)
        db.commit()
        print(f"\n{len(chamados)} chamado(s) apagado(s) com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
