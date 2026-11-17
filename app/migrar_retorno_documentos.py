"""
Cria a tabela retorno_documentos - o retorno mensal dos documentos
assinados de cada colaborador (ponto, holerite, VA/VT, ficha de EPI),
que antes era a planilha "Retorno de documentos.xlsx". O historico da
planilha e importado pela tela Retorno de documentos (botao Importar
planilha), nao por aqui.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_retorno_documentos.py
"""

import models
from database import engine


def main():
    models.RetornoDocumento.__table__.create(engine, checkfirst=True)
    print("Tabela retorno_documentos OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
