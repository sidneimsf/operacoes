"""
Localiza no mapa (latitude/longitude) os clientes ativos que ainda nao
tem posicao, a partir do endereco/bairro/cidade cadastrados. Clientes
novos ou com endereco alterado ja sao localizados na hora de salvar;
este script serve para a carga inicial e para tentar de novo os que
falharam.

Respeita o limite do Nominatim (1 consulta por segundo), entao demora
alguns minutos para ~160 clientes. Pode rodar mais de uma vez: so mexe
em quem esta sem posicao (nunca sobrescreve um pino ajustado a mao).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python geocodificar_clientes.py
"""

import time

from database import SessionLocal
from geocodificacao import localizar_endereco
from models import Cliente


def main():
    db = SessionLocal()
    try:
        pendentes = (
            db.query(Cliente)
            .filter(Cliente.ativo.is_(True), Cliente.latitude.is_(None))
            .order_by(Cliente.nome)
            .all()
        )
        print(f"{len(pendentes)} cliente(s) sem posicao no mapa")
        achados_endereco = achados_bairro = sem_resultado = 0

        for cliente in pendentes:
            if not cliente.endereco and not cliente.bairro:
                print(f"  - {cliente.nome}: sem endereco nem bairro cadastrado, pulando")
                sem_resultado += 1
                continue
            resultado = localizar_endereco(cliente.endereco, cliente.bairro, cliente.cidade or cliente.municipio)
            if resultado is None:
                print(f"  - {cliente.nome}: nao encontrado")
                sem_resultado += 1
            else:
                cliente.latitude, cliente.longitude, cliente.geo_precisao = resultado
                db.commit()
                if cliente.geo_precisao == "endereco":
                    achados_endereco += 1
                else:
                    achados_bairro += 1
                print(f"  + {cliente.nome}: {cliente.geo_precisao}")
            time.sleep(1.1)

        print(
            f"Pronto: {achados_endereco} pelo endereco, {achados_bairro} aproximados pelo bairro, "
            f"{sem_resultado} sem posicao (ajuste esses direto no Mapa de Clientes)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
