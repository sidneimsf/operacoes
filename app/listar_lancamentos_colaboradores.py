"""
Lista todos os lancamentos da linha do tempo dos colaboradores
(anotacao, documento, atestado, falta, ferias, advertencia, ASO,
etc). Nao apaga nada - so mostra.

ATENCAO: os 83 registros do tipo "aso" carregados pela migracao
migrar_asos.py sao dados REAIS, nao de teste - cuidado pra nao
confundir com lancamentos de teste.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python listar_lancamentos_colaboradores.py
"""

from database import SessionLocal
from models import ColaboradorEvento


def main():
    db = SessionLocal()
    try:
        eventos = db.query(ColaboradorEvento).order_by(ColaboradorEvento.criado_em.asc()).all()
        print(f"Total de lancamentos: {len(eventos)}\n")
        for e in eventos:
            descricao = (e.descricao or "").replace("\n", " ")[:40]
            print(
                f"id={e.id:4d} | {e.criado_em.strftime('%d/%m/%Y %H:%M')} | "
                f"colaborador={e.colaborador.nome[:25]:25s} | tipo={e.tipo:12s} | "
                f"registrado_por={e.registrado_por.nome:15s} | descricao={descricao}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
