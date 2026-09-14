"""
Adiciona o suporte a "Posto Vago":
- coluna eh_posto_vago em colaboradores
- cria o registro unico "POSTO VAGO" (pseudo-colaborador, nao conta nas
  estatisticas normais, mas fica selecionavel no Mapa de Servico)
- tabela confirmacoes_posto_vago (pro alerta de "amanha fulano de
  posto vago" com botao de confirmar)

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_posto_vago.py
"""

from sqlalchemy import text

import models
from database import SessionLocal, engine


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE colaboradores ADD COLUMN IF NOT EXISTS eh_posto_vago BOOLEAN NOT NULL DEFAULT false"))
    print("executado: coluna eh_posto_vago adicionada em colaboradores")

    models.ConfirmacaoPostoVago.__table__.create(engine, checkfirst=True)
    print("executado: tabela confirmacoes_posto_vago OK (criada ou ja existente)")

    db = SessionLocal()
    try:
        ja_existe = db.query(models.Colaborador).filter_by(eh_posto_vago=True).first()
        if ja_existe:
            print("registro POSTO VAGO ja existe (id={})".format(ja_existe.id))
        else:
            primeira_empresa = db.query(models.Empresa).first()
            if primeira_empresa is None:
                print("AVISO: nenhuma empresa cadastrada ainda - rode esta migracao de novo depois de cadastrar a primeira empresa")
                return
            posto_vago = models.Colaborador(
                empresa_id=primeira_empresa.id,
                nome="POSTO VAGO",
                status="ativo",
                eh_posto_vago=True,
            )
            db.add(posto_vago)
            db.commit()
            print("registro POSTO VAGO criado com sucesso (id={})".format(posto_vago.id))
    finally:
        db.close()


if __name__ == "__main__":
    main()
