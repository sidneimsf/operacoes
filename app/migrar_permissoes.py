"""
Adiciona o sistema de permissoes configuraveis: coluna super_admin em
usuarios, e a tabela usuario_permissoes. Marca Caroline e Sidnei como
super_admin (sao os unicos que podem gerenciar permissoes dos outros).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_permissoes.py
"""

from sqlalchemy import text

import models
from database import SessionLocal, engine
from models import Usuario

COMANDOS_ALTER = [
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS super_admin BOOLEAN DEFAULT FALSE",
]

NOMES_SUPER_ADMIN = ["Sidnei", "Caroline"]


def main():
    with engine.begin() as conn:
        for comando in COMANDOS_ALTER:
            conn.execute(text(comando))
            print("executado:", comando)

    models.UsuarioPermissao.__table__.create(engine, checkfirst=True)
    print("Tabela usuario_permissoes OK (criada ou ja existente)")

    db = SessionLocal()
    try:
        marcados = []
        for nome in NOMES_SUPER_ADMIN:
            usuario = db.query(Usuario).filter(Usuario.nome.ilike(f"{nome}%")).first()
            if usuario is None:
                print(f"atencao: usuario '{nome}' nao encontrado, pulando")
                continue
            usuario.super_admin = True
            marcados.append(usuario.nome)
        db.commit()
        print("")
        print("Marcados como super_admin:", marcados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
