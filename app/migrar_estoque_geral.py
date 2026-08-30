"""
Reorganiza o estoque: so a CAMISETA precisa ficar separada por
empresa (por causa da logo impressa). Todos os outros itens (calca,
sapato, moletom, etc.) passam a ser um estoque GERAL, compartilhado
entre todas as empresas - a empresa desses itens vira nula.

Se, depois dessa mudanca, dois itens acabarem com o mesmo tipo+tamanho
(por exemplo, se duas empresas ja tivessem "CALCA P" cadastrada
separadamente), as quantidades sao somadas num so registro, e o
historico de movimentacoes e reatribuido pra ele, sem perder nada.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_estoque_geral.py
"""

from database import SessionLocal
from models import EstoqueItem, EstoqueMovimento


def main():
    db = SessionLocal()
    try:
        itens_nao_camiseta = db.query(EstoqueItem).filter(EstoqueItem.tipo_peca != "CAMISETA").all()

        total_reclassificados = 0
        for item in itens_nao_camiseta:
            if item.empresa_id is None:
                continue
            item.empresa_id = None
            total_reclassificados += 1
        db.flush()

        todos_gerais = (
            db.query(EstoqueItem)
            .filter(EstoqueItem.empresa_id.is_(None))
            .order_by(EstoqueItem.id)
            .all()
        )
        vistos = {}
        total_fundidos = 0
        for item in todos_gerais:
            chave = (item.tipo_peca, item.tamanho)
            if chave not in vistos:
                vistos[chave] = item
                continue

            principal = vistos[chave]
            principal.quantidade_atual += item.quantidade_atual

            movimentos = db.query(EstoqueMovimento).filter_by(item_id=item.id).all()
            for m in movimentos:
                m.item_id = principal.id

            db.delete(item)
            total_fundidos += 1

        db.commit()
        print("Itens reclassificados para 'Geral':", total_reclassificados)
        print("Itens duplicados fundidos (mesma peca+tamanho):", total_fundidos)
    finally:
        db.close()


if __name__ == "__main__":
    main()
