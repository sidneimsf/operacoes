"""
Cria as tabelas de veiculos e manutencoes de veiculo.

Nao cadastra nenhum veiculo automaticamente - use o botao
"+ Novo veiculo" na tela de Veiculos para cadastrar os 2 Fiat Mobi
reais da empresa (com a placa e o km atual verdadeiros).

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_veiculos.py
"""

import models
from database import engine


def main():
    models.Veiculo.__table__.create(engine, checkfirst=True)
    models.ManutencaoVeiculo.__table__.create(engine, checkfirst=True)
    print("Tabelas de veiculos OK (criadas ou ja existentes)")
    print("Va em Veiculos no sistema e clique em '+ Novo veiculo' para")
    print("cadastrar os 2 Fiat Mobi reais da empresa.")


if __name__ == "__main__":
    main()
