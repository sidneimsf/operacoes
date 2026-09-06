"""
Adiciona colaborador_id e acao_corretiva na tabela chamados, e cria um
cliente especial "ESCRITORIO ADM" (dentro de uma empresa "ADMINISTRATIVO"
tambem nova), usado quando um chamado e um assunto interno entre
supervisor e escritorio, e nao sobre um cliente de verdade.

Idempotente: pode rodar mais de uma vez sem duplicar nada.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_chamado_colaborador_e_adm.py
"""

from sqlalchemy import text

from database import SessionLocal, engine
from models import Cliente, Empresa


def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS colaborador_id INTEGER REFERENCES colaboradores(id)"))
        conn.execute(text("ALTER TABLE chamados ADD COLUMN IF NOT EXISTS acao_corretiva VARCHAR(1500)"))
        print("executado: colunas colaborador_id e acao_corretiva adicionadas em chamados")

    db = SessionLocal()
    try:
        empresa_adm = db.query(Empresa).filter_by(nome="ADMINISTRATIVO").first()
        if empresa_adm is None:
            empresa_adm = Empresa(nome="ADMINISTRATIVO")
            db.add(empresa_adm)
            db.flush()
            print("Empresa 'ADMINISTRATIVO' criada")
        else:
            print("Empresa 'ADMINISTRATIVO' ja existia")

        cliente_adm = db.query(Cliente).filter_by(nome="ESCRITÓRIO ADM").first()
        if cliente_adm is None:
            cliente_adm = Cliente(empresa_id=empresa_adm.id, nome="ESCRITÓRIO ADM")
            db.add(cliente_adm)
            print("Cliente 'ESCRITÓRIO ADM' criado")
        else:
            print("Cliente 'ESCRITÓRIO ADM' ja existia")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
