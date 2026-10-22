"""
Localiza no mapa (latitude/longitude) os clientes ativos que ainda nao
tem posicao, a partir do endereco/bairro/cidade/UF/CEP cadastrados.
Clientes novos ou com endereco alterado ja sao localizados na hora de
salvar; a importacao de enderecos pela planilha usa a versao em segundo
plano (iniciar_em_segundo_plano). Rodar este script serve para tentar de
novo os que falharam.

Respeita o limite do Nominatim (1 consulta por segundo), entao demora
alguns minutos para ~200 clientes. So mexe em quem esta sem posicao
(nunca sobrescreve um pino ajustado a mao).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python geocodificar_clientes.py
"""

import threading

from database import SessionLocal
from geocodificacao import localizar_endereco
from models import Cliente

_trava = threading.Lock()
_situacao = {"em_andamento": False, "restantes": 0}


def localizar_cliente(cliente: Cliente) -> bool:
    """Atualiza o pino do cliente pelo endereco cadastrado. Devolve se achou."""
    resultado = localizar_endereco(
        cliente.endereco, cliente.bairro, cliente.cidade or cliente.municipio, cliente.uf, cliente.cep
    )
    if resultado is None:
        cliente.latitude = cliente.longitude = cliente.geo_precisao = None
        return False
    cliente.latitude, cliente.longitude, cliente.geo_precisao = resultado
    return True


def localizar_pendentes(mostrar=print) -> dict:
    """Localiza todos os clientes ativos sem posicao, um por vez, salvando a cada um."""
    db = SessionLocal()
    contagem = {"endereco": 0, "cep": 0, "bairro": 0, "sem_posicao": 0}
    try:
        ids = [
            c.id
            for c in db.query(Cliente.id)
            .filter(Cliente.ativo.is_(True), Cliente.latitude.is_(None))
            .order_by(Cliente.nome)
        ]
        _situacao["restantes"] = len(ids)
        mostrar(f"{len(ids)} cliente(s) sem posicao no mapa")
        for cliente_id in ids:
            cliente = db.get(Cliente, cliente_id)
            if not cliente.endereco and not cliente.bairro and not cliente.cep:
                mostrar(f"  - {cliente.nome}: sem endereco, bairro nem CEP cadastrado, pulando")
                contagem["sem_posicao"] += 1
            elif localizar_cliente(cliente):
                db.commit()
                contagem[cliente.geo_precisao] += 1
                mostrar(f"  + {cliente.nome}: {cliente.geo_precisao}")
            else:
                mostrar(f"  - {cliente.nome}: nao encontrado")
                contagem["sem_posicao"] += 1
            _situacao["restantes"] -= 1
    finally:
        db.close()
    mostrar(
        f"Pronto: {contagem['endereco']} pelo endereco, {contagem['cep']} pelo CEP, "
        f"{contagem['bairro']} aproximados pelo bairro, {contagem['sem_posicao']} sem posicao "
        "(ajuste esses direto no Mapa de Clientes)"
    )
    return contagem


def _rodar_em_segundo_plano():
    try:
        localizar_pendentes(mostrar=lambda texto: None)
    except Exception as erro:
        print(f"geocodificar_clientes: falha na localizacao em segundo plano: {erro}")
    finally:
        _situacao["em_andamento"] = False
        _situacao["restantes"] = 0
        _trava.release()


def iniciar_em_segundo_plano() -> bool:
    """Dispara a localizacao dos pendentes numa thread. Se ja tiver uma rodando, nao inicia outra
    (a que esta rodando pega os pendentes novos na proxima vez que alguem pedir)."""
    if not _trava.acquire(blocking=False):
        return False
    _situacao["em_andamento"] = True
    threading.Thread(target=_rodar_em_segundo_plano, daemon=True).start()
    return True


def situacao() -> dict:
    return dict(_situacao)


if __name__ == "__main__":
    localizar_pendentes()
