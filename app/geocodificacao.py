"""
Transforma o endereco de um cliente em latitude/longitude, usando o
Nominatim (OpenStreetMap) - gratuito, sem chave de API.

Regras de uso do Nominatim: no maximo 1 consulta por segundo e um
User-Agent que identifique o sistema. Por isso a localizacao em lote
(geocodificar_clientes.py) espera entre um cliente e outro, e ao salvar
um cliente fazemos no maximo 3 consultas, com 1 segundo entre elas.
"""

import json
import time
import urllib.parse
import urllib.request

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "operacoes-mapa-clientes/1.0 (operacoes.cordsul.com.br)"
TIMEOUT_SEGUNDOS = 5


def _consultar(texto: str) -> tuple[float, float] | None:
    parametros = urllib.parse.urlencode({"q": texto, "format": "json", "limit": 1, "countrycodes": "br"})
    requisicao = urllib.request.Request(f"{URL_NOMINATIM}?{parametros}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
        resultados = json.loads(resposta.read().decode("utf-8"))
    if not resultados:
        return None
    return float(resultados[0]["lat"]), float(resultados[0]["lon"])


def localizar_endereco(
    endereco: str | None, bairro: str | None, cidade: str | None
) -> tuple[float, float, str] | None:
    """
    Tenta primeiro o endereco completo; se nao achar, cai para o centro
    do bairro (pino aproximado). Devolve (latitude, longitude, precisao)
    ou None. Nunca levanta erro - falha de rede vira None, pra nao
    impedir de salvar o cliente.
    """
    sufixo = ([cidade] if cidade else []) + ["Brasil"]
    tentativas = []
    if endereco:
        if bairro:
            tentativas.append((", ".join([endereco, bairro] + sufixo), "endereco"))
        tentativas.append((", ".join([endereco] + sufixo), "endereco"))
    if bairro and cidade:
        tentativas.append((", ".join([bairro] + sufixo), "bairro"))

    for indice, (texto, precisao) in enumerate(tentativas):
        if indice > 0:
            time.sleep(1)  # limite do Nominatim: 1 consulta por segundo
        try:
            achado = _consultar(texto)
        except Exception as erro:
            print(f"geocodificacao: falha ao consultar '{texto}': {erro}")
            return None
        if achado is not None:
            return achado[0], achado[1], precisao
    return None
