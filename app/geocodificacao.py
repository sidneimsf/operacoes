"""
Transforma o endereco de um cliente em latitude/longitude, usando o
Nominatim (OpenStreetMap) - gratuito, sem chave de API.

Regras de uso do Nominatim: no maximo 1 consulta por segundo e um
User-Agent que identifique o sistema. Por isso toda consulta passa por
_consultar(), que garante o intervalo minimo entre uma e outra.
"""

import json
import re
import threading
import time
import urllib.parse
import urllib.request

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "operacoes-mapa-clientes/1.0 (operacoes.cordsul.com.br)"
TIMEOUT_SEGUNDOS = 5
INTERVALO_MINIMO_SEGUNDOS = 1.1

_trava_intervalo = threading.Lock()
_ultima_consulta = 0.0

# abreviacoes comuns nas planilhas -> forma por extenso que o OpenStreetMap conhece
ABREVIACOES = [
    (r"^R\.?\s+", "Rua "),
    (r"^Av\.?\s+", "Avenida "),
    (r"^Rod\.?\s+", "Rodovia "),
    (r"^Tv\.?\s+", "Travessa "),
    (r"^Al\.?\s+", "Alameda "),
    (r"^Est\.?\s+", "Estrada "),
    (r"^Srv\.?\s+", "Servidao "),
    (r"\bMal\.\s*", "Marechal "),
    (r"\bDr\.\s*", "Doutor "),
    (r"\bDra\.\s*", "Doutora "),
    (r"\bProf\.\s*", "Professor "),
    (r"\bPe\.\s*", "Padre "),
    (r"\bSto\.\s*", "Santo "),
    (r"\bSta\.\s*", "Santa "),
    (r"\bN\.?\s*Sra\.?\s*", "Nossa Senhora "),
    (r"\bSra\.\s*", "Senhora "),
    (r"\bCel\.\s*", "Coronel "),
    (r"\bGov\.\s*", "Governador "),
    (r"\bPres\.\s*", "Presidente "),
    (r"\bDep\.\s*", "Deputado "),
    (r"\bVer\.\s*", "Vereador "),
    (r"\bEng\.\s*", "Engenheiro "),
]


def limpar_endereco(endereco: str) -> str:
    """
    Deixa so 'logradouro, numero': tira complemento (sala, bloco, galpao,
    lote...), que atrapalha a busca, e escreve as abreviacoes por extenso.
    Ex: 'Av. Mal. Castelo Branco, 65 - Torre B Sala 301' -> 'Avenida Marechal Castelo Branco, 65'
    """
    texto = endereco.replace("\xa0", " ").strip()
    texto = re.split(r"\s+[-–—]\s+", texto)[0]  # complemento depois de " - "
    partes = [p.strip() for p in texto.split(",")]
    texto = ", ".join(partes[:2])  # logradouro e numero; o resto costuma ser complemento
    texto = re.sub(r"\bs/?n[ºo°]?\b\.?", "", texto, flags=re.IGNORECASE).strip(" ,")
    for padrao, troca in ABREVIACOES:
        texto = re.sub(padrao, troca, texto, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", texto).strip(" ,")


def _consultar(parametros: dict) -> tuple[float, float] | None:
    global _ultima_consulta
    with _trava_intervalo:
        espera = INTERVALO_MINIMO_SEGUNDOS - (time.monotonic() - _ultima_consulta)
        if espera > 0:
            time.sleep(espera)
        _ultima_consulta = time.monotonic()
    consulta = urllib.parse.urlencode({**parametros, "format": "json", "limit": 1, "countrycodes": "br"})
    requisicao = urllib.request.Request(f"{URL_NOMINATIM}?{consulta}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
        resultados = json.loads(resposta.read().decode("utf-8"))
    if not resultados:
        return None
    return float(resultados[0]["lat"]), float(resultados[0]["lon"])


def localizar_endereco(
    endereco: str | None,
    bairro: str | None,
    cidade: str | None,
    uf: str | None = None,
    cep: str | None = None,
) -> tuple[float, float, str] | None:
    """
    Tenta do mais preciso pro menos preciso: endereco completo, endereco
    sem bairro, CEP e, por ultimo, o centro do bairro (pino aproximado).
    Devolve (latitude, longitude, precisao) ou None. Nunca levanta erro -
    falha de rede vira None, pra nao impedir de salvar o cliente.
    """
    regiao = [p for p in (cidade, uf) if p]
    tentativas = []
    if endereco:
        rua = limpar_endereco(endereco)
        if cidade:
            tentativas.append(({"street": rua, "city": cidade, **({"state": uf} if uf else {}), "country": "Brasil"}, "endereco"))
        if bairro:
            tentativas.append(({"q": ", ".join([rua, bairro] + regiao + ["Brasil"])}, "endereco"))
        tentativas.append(({"q": ", ".join([rua] + regiao + ["Brasil"])}, "endereco"))
    if cep and re.fullmatch(r"\d{5}-?\d{3}", cep.strip()):
        digitos = re.sub(r"\D", "", cep)
        tentativas.append(({"postalcode": f"{digitos[:5]}-{digitos[5:]}", "country": "Brasil"}, "cep"))
    if bairro and cidade:
        tentativas.append(({"q": ", ".join([bairro] + regiao + ["Brasil"])}, "bairro"))

    for parametros, precisao in tentativas:
        try:
            achado = _consultar(parametros)
        except Exception as erro:
            print(f"geocodificacao: falha ao consultar {parametros}: {erro}")
            return None
        if achado is not None:
            return achado[0], achado[1], precisao
    return None
