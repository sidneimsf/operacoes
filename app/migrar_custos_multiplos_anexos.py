"""
Cria a tabela custos_diarios_anexos (permite varios comprovantes por
custo diario, anexados a qualquer momento) e migra os comprovantes
antigos (coluna unica comprovante_path) para essa nova tabela.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_custos_multiplos_anexos.py
"""

import models
from database import SessionLocal, engine


def main():
    models.CustoDiarioAnexo.__table__.create(engine, checkfirst=True)
    print("executado: tabela custos_diarios_anexos criada (ou ja existente)")

    db = SessionLocal()
    try:
        custos_com_comprovante_antigo = (
            db.query(models.CustoDiario)
            .filter(models.CustoDiario.comprovante_path.isnot(None))
            .all()
        )
        migrados = 0
        for custo in custos_com_comprovante_antigo:
            ja_migrado = (
                db.query(models.CustoDiarioAnexo)
                .filter_by(custo_diario_id=custo.id, arquivo_path=custo.comprovante_path)
                .first()
            )
            if ja_migrado:
                continue
            db.add(models.CustoDiarioAnexo(
                custo_diario_id=custo.id,
                arquivo_path=custo.comprovante_path,
                arquivo_nome_original=custo.comprovante_nome_original or "comprovante",
            ))
            migrados += 1
        db.commit()
        print(f"executado: {migrados} comprovante(s) antigo(s) migrado(s) para a nova tabela")
    finally:
        db.close()


if __name__ == "__main__":
    main()
