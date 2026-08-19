"""
Cria as tabelas no banco de dados, a partir dos modelos definidos em models.py.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python init_db.py
"""

import models  # noqa: F401  (garante que os modelos sejam registrados no Base)
from database import Base, engine


def main():
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso: empresas, clientes, colaboradores")


if __name__ == "__main__":
    main()
