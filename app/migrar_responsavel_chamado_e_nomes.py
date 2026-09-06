"""
Adiciona a coluna disponivel_responsavel_chamado em usuarios (default
True pra todo mundo), depois desmarca Sidnei e Flavio especificamente
(eles continuam podendo USAR o sistema normalmente, so nao aparecem
mais como opcao de responsavel ao abrir um chamado).

Tambem corrige a capitalizacao do nome da Jessica.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_responsavel_chamado_e_nomes.py
"""

from sqlalchemy import text

from database import SessionLocal, engine
from models import Usuario

NOMES_PARA_REMOVER_DE_RESPONSAVEL = ["Sidnei", "Flavio", "Flávio"]


def main():
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS "
                "disponivel_responsavel_chamado BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )
        print("executado: coluna disponivel_responsavel_chamado adicionada")

    db = SessionLocal()
    try:
        for nome in NOMES_PARA_REMOVER_DE_RESPONSAVEL:
            usuario = db.query(Usuario).filter_by(nome=nome).first()
            if usuario is not None:
                usuario.disponivel_responsavel_chamado = False
                print(f"'{usuario.nome}' removido das opcoes de responsavel de chamado")

        jessica = db.query(Usuario).filter(Usuario.nome.ilike("jessica")).first()
        if jessica is not None:
            jessica.nome = "Jessica"
            print("Nome da Jessica corrigido para 'Jessica'")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
