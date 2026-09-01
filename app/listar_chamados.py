"""
Lista todos os chamados cadastrados, pra ajudar a identificar quais
sao de teste antes de apagar. Nao apaga nada - so mostra.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python listar_chamados.py
"""

from database import SessionLocal
from models import Chamado


def main():
    db = SessionLocal()
    try:
        chamados = db.query(Chamado).order_by(Chamado.criado_em.asc()).all()
        print(f"Total de chamados: {len(chamados)}\n")
        for c in chamados:
            print(
                f"id={c.id:4d} | {c.criado_em.strftime('%d/%m/%Y %H:%M')} | "
                f"cliente={c.cliente.nome[:30]:30s} | tipo={c.tipo:15s} | "
                f"status={c.status:12s} | aberto_por={c.aberto_por.nome:15s} | "
                f"descricao={c.descricao[:40]}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
