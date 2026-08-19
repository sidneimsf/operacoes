"""
Cria um usuario (supervisor ou escritorio) de forma interativa.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao (com -it para o modo interativo):
    docker compose exec -it app python criar_usuario.py
"""

import getpass

from database import SessionLocal
from models import Usuario
from security import hash_senha

PAPEIS_VALIDOS = {"supervisor", "escritorio"}


def main():
    print("== Criar novo usuario ==")
    nome = input("Nome: ").strip()
    email = input("Email: ").strip().lower()

    papel = ""
    while papel not in PAPEIS_VALIDOS:
        papel = input("Papel (supervisor/escritorio): ").strip().lower()

    senha = getpass.getpass("Senha: ")
    senha_confirmacao = getpass.getpass("Confirme a senha: ")

    if senha != senha_confirmacao:
        print("As senhas nao coincidem. Nada foi criado.")
        return

    db = SessionLocal()
    try:
        existente = db.query(Usuario).filter_by(email=email).first()
        if existente:
            print(f"Ja existe um usuario com o email {email}. Nada foi criado.")
            return

        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=hash_senha(senha),
            papel=papel,
        )
        db.add(usuario)
        db.commit()
        print(f"Usuario criado: {nome} ({email}) - papel: {papel}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
