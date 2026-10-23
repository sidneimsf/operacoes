"""
Audios das visitas comerciais: transcricao local (Whisper, sem API paga),
extracao de campos a partir do texto transcrito e limpeza dos audios com
mais de 48 horas. Usado pelos jobs do agendador em main.py.

A extracao e feita por padroes (regex), nao por IA: reconhece bem
telefone, e-mail, valor, quantidade de postos, tipo de servico, horarios
e datas faladas; nome de contato, bairro e nome do local so quando o
supervisor usa frases previsiveis ("falei com a sindica Maria", "no
bairro Centro", "condominio Jardins").
"""

import os
import re
import threading
import unicodedata
from datetime import date, datetime, timedelta, timezone

from database import SessionLocal
from models import VisitaComercial, VisitaComercialAudio

WHISPER_MODELO = os.environ.get("WHISPER_MODELO", "small")
HORAS_GUARDAR_AUDIO = 48
# a gravacao no navegador para sozinha em 30s; a folga cobre o atraso do gravador.
# Audio mais longo nem e transcrito - transcrever audio longo estourou a memoria da VPS
LIMITE_AUDIO_SEGUNDOS = 30
FOLGA_LIMITE_AUDIO_SEGUNDOS = 5
# um audio "processando" ha mais tempo que isso ficou orfao (container reiniciou no meio)
LIMITE_PROCESSANDO = timedelta(minutes=30)

_modelo = None
_trava_modelo = threading.Lock()


def _carregar_modelo():
    """Carrega o Whisper uma vez so (~1 GB de RAM no modelo small) e reaproveita."""
    global _modelo
    with _trava_modelo:
        if _modelo is None:
            from faster_whisper import WhisperModel

            # metade dos nucleos, pra transcricao nao deixar o sistema lento pros usuarios
            threads = max(1, (os.cpu_count() or 2) // 2)
            _modelo = WhisperModel(WHISPER_MODELO, device="cpu", compute_type="int8", cpu_threads=threads)
    return _modelo


class AudioLongoDemais(Exception):
    pass


def transcrever_arquivo(caminho: str) -> tuple[str, float]:
    """Devolve (texto, duracao_em_segundos). Recusa audio acima do limite antes de rodar o Whisper."""
    from faster_whisper import decode_audio

    amostras = decode_audio(caminho, sampling_rate=16000)
    if len(amostras) / 16000 > LIMITE_AUDIO_SEGUNDOS + FOLGA_LIMITE_AUDIO_SEGUNDOS:
        raise AudioLongoDemais()
    segmentos, info = _carregar_modelo().transcribe(amostras, language="pt", vad_filter=True, beam_size=5)
    texto = " ".join(s.text.strip() for s in segmentos).strip()
    return texto, info.duration


# ---------------------------------------------------------------------------
# Extracao de campos a partir do texto
# ---------------------------------------------------------------------------

NUMEROS_POR_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "quinze": 15, "vinte": 20,
}

DIAS_SEMANA = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}

# palavra-chave (sem acento) -> chave de TIPOS_SERVICO_COMERCIAL em main.py
PALAVRAS_TIPO_SERVICO = [
    (r"portaria", "portaria"),
    (r"limpeza|faxin|conservacao|higienizacao|servicos gerais", "limpeza"),
    (r"zeladoria", "zeladoria"),
    (r"recepcao|recepcionista", "recepcao"),
    (r"jardinagem|jardineir", "jardinagem"),
    (r"manutencao", "manutencao"),
]

CARGOS_CONTATO = (
    r"sindic[oa]|subsindic[oa]|zelador[a]?|gerente|administrador[a]?|dono|dona|proprietari[oa]"
    r"|coordenador[a]?|supervisor[a]?|diretor[a]?|encarregad[oa]|porteir[oa]|recepcionista|responsavel"
)

# palavras que indicam que a data falada e de retorno/compromisso, nao da visita
GATILHOS_RETORNO = r"retorn|volt|ligar|liga|enviar|mandar|proposta|ate|combin|agend|reuni"

def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _numero(token: str) -> int | None:
    token = _sem_acento(token.lower())
    if token.isdigit():
        return int(token)
    return NUMEROS_POR_EXTENSO.get(token)


def _extrair_telefone(texto: str) -> str | None:
    for candidato in re.finditer(r"\(?\d[\d\s().-]{7,18}\d", texto):
        digitos = re.sub(r"\D", "", candidato.group())
        if digitos.startswith("55") and len(digitos) in (12, 13):
            digitos = digitos[2:]
        if len(digitos) == 11:
            return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
        if len(digitos) == 10:
            return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
        if len(digitos) == 9:
            return f"{digitos[:5]}-{digitos[5:]}"
    return None


def _extrair_email(texto: str) -> str | None:
    """Aceita o e-mail escrito ou falado ("joao arroba gmail ponto com ponto br")."""
    sem_acento = _sem_acento(texto.lower())
    separador = r"(?:\s+ponto\s+|\.(?=\w))"
    achado = re.search(
        r"([\w+-]+(?:" + separador + r"[\w+-]+)*)\s*(?:@|\barroba\b)\s*([\w-]+(?:" + separador + r"[\w-]+)+)",
        sem_acento,
    )
    if not achado:
        return None
    usuario = re.sub(separador, ".", achado.group(1))
    dominio = re.sub(separador, ".", achado.group(2))
    return f"{usuario}@{dominio}"


def _valor_brasileiro(numero: str) -> float:
    """'12.500,50' -> 12500.5 ; '12,5' -> 12.5 ; '12.500' -> 12500"""
    if "," in numero:
        return float(numero.replace(".", "").replace(",", "."))
    partes = numero.split(".")
    if len(partes) > 1 and all(len(p) == 3 for p in partes[1:]):
        return float("".join(partes))
    return float(numero)


def _extrair_valor(texto: str) -> float | None:
    sem_acento = _sem_acento(texto.lower())
    achado = re.search(r"(\d+(?:[.,]\d+)*)\s*mil\b", sem_acento)
    if achado:
        return round(_valor_brasileiro(achado.group(1)) * 1000, 2)
    achado = re.search(r"r\$\s*(\d+(?:[.,]\d+)*)", sem_acento)
    if achado:
        return _valor_brasileiro(achado.group(1))
    achado = re.search(r"(\d+(?:[.,]\d+)*)\s*reais", sem_acento)
    if achado:
        return _valor_brasileiro(achado.group(1))
    return None


def _extrair_qtd_postos(texto: str) -> int | None:
    sem_acento = _sem_acento(texto.lower())
    achado = re.search(
        r"\b(\d+|" + "|".join(NUMEROS_POR_EXTENSO) + r")\s+"
        r"(postos?|colaborador(?:es|as?)?|funcionari[oa]s?|porteir[oa]s?|zelador(?:es|as?)?|faxineir[oa]s?"
        r"|vigias?|vigilantes?|recepcionistas?|jardineir[oa]s?|pessoas)\b",
        sem_acento,
    )
    return _numero(achado.group(1)) if achado else None


def _extrair_tipo_servico(texto: str) -> str | None:
    sem_acento = _sem_acento(texto.lower())
    encontrados = []
    for padrao, chave in PALAVRAS_TIPO_SERVICO:
        achado = re.search(padrao, sem_acento)
        if achado:
            encontrados.append((achado.start(), chave))
    return min(encontrados)[1] if encontrados else None


def _extrair_horarios(texto: str) -> str | None:
    sem_acento = _sem_acento(texto.lower())
    if re.search(r"\b24\s*(?:h\b|horas)", sem_acento):
        return "24 horas"
    achado = re.search(r"\bdas?\s+(\d{1,2})(?:[:h](\d{2}))?\s*(?:h|horas)?\s+(?:as|ate)\s+(\d{1,2})(?:[:h](\d{2}))?", sem_acento)
    if not achado:
        return None
    inicio = f"{achado.group(1)}h{achado.group(2) or ''}"
    fim = f"{achado.group(3)}h{achado.group(4) or ''}"
    dias = re.search(r"(segunda|domingo)\s+a\s+(sexta|sabado|domingo)", sem_acento)
    prefixo = f"{dias.group(1)} a {dias.group(2)}, " if dias else ""
    return f"{prefixo}{inicio} às {fim}".replace("sabado", "sábado")


def _datas_faladas(texto: str, hoje: date) -> list[tuple[int, date]]:
    """Lista (posicao_no_texto, data) de cada data reconhecida."""
    sem_acento = _sem_acento(texto.lower())
    datas = []
    for achado in re.finditer(r"depois de amanha|amanha|semana que vem|proxima semana", sem_acento):
        dias = {"depois de amanha": 2, "amanha": 1}.get(achado.group(), 7)
        datas.append((achado.start(), hoje + timedelta(days=dias)))
    for achado in re.finditer(r"\b(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:-feira| feira)?\b", sem_acento):
        # "de segunda a sexta" descreve horario, nao data
        if re.search(r"\b(?:de\s+)?" + achado.group(1) + r"(?:-feira| feira)?\s+a\s+", sem_acento[achado.start():achado.start() + 25]):
            continue
        if re.search(r"\ba\s+$", sem_acento[max(0, achado.start() - 3):achado.start()]):
            continue
        dias = (DIAS_SEMANA[achado.group(1)] - hoje.weekday() - 1) % 7 + 1
        datas.append((achado.start(), hoje + timedelta(days=dias)))
    for achado in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", sem_acento):
        dia, mes = int(achado.group(1)), int(achado.group(2))
        ano = int(achado.group(3)) if achado.group(3) else hoje.year
        if ano < 100:
            ano += 2000
        try:
            data = date(ano, mes, dia)
        except ValueError:
            continue
        if not achado.group(3) and data < hoje:
            data = date(ano + 1, mes, dia)
        datas.append((achado.start(), data))
    for achado in re.finditer(r"\bdia\s+(\d{1,2})\b(?!\s*/)", sem_acento):
        dia = int(achado.group(1))
        ano, mes = hoje.year, hoje.month
        if dia < hoje.day:
            mes += 1
            if mes > 12:
                ano, mes = ano + 1, 1
        try:
            datas.append((achado.start(), date(ano, mes, dia)))
        except ValueError:
            continue
    return sorted(datas)


def _extrair_data_retorno(texto: str, hoje: date) -> date | None:
    sem_acento = _sem_acento(texto.lower())
    for posicao, data in _datas_faladas(texto, hoje):
        if data > hoje and re.search(GATILHOS_RETORNO, sem_acento[max(0, posicao - 60):posicao]):
            return data
    return None


def _base(texto: str) -> str:
    """Texto sem acento e com o MESMO tamanho do original (transcricao vem
    em NFC), pra buscar com regex simples e recortar o original pelas
    mesmas posicoes - assim o nome volta com acento."""
    base = _sem_acento(texto)
    return base if len(base) == len(texto) else texto


NOME = r"[A-Z][a-z]+(?:\s+(?:de|do|da|dos|das)\s+[A-Z][a-z]+|\s+[A-Z][a-z]+)?"


def _extrair_contato(texto: str) -> tuple[str | None, str | None]:
    base = _base(texto)
    achado = re.search(
        r"(?i:falei com|conversei com|fui atendid[oa] por|o contato (?:e|foi)|(?:o|a) responsavel (?:e|foi))\s+"
        r"(?:(?i:o|a|seu|sua|senhor|senhora|sr\.?|sra\.?)\s+)?"
        r"(?:(?i:(" + CARGOS_CONTATO + r"))\s*,?\s+)?"
        r"(?:(?i:o|a|seu|sua|dona|senhor|senhora)\s+)?"
        r"(" + NOME + r")?",
        base,
    )
    if not achado:
        return None, None
    cargo = texto[achado.start(1):achado.end(1)] if achado.group(1) else None
    nome = texto[achado.start(2):achado.end(2)] if achado.group(2) else None
    return nome, cargo.capitalize() if cargo else None


def _extrair_depois_de(texto: str, gatilho: str) -> str | None:
    base = _base(texto)
    achado = re.search(r"(?i:" + gatilho + r")\s+(?:(?i:de|do|da)\s+)?(" + NOME + r")", base)
    return texto[achado.start(1):achado.end(1)] if achado else None


def _extrair_nome_local(texto: str) -> str | None:
    base = _base(texto)
    achado = re.search(
        r"\b(?i:(condominio|edificio|residencial|predio|empresa|loja|escola|clinica|hospital|hotel|shopping|galpao|fabrica|igreja|academia))"
        r"\s+((?:" + NOME + r"|\d+)(?:\s+(?:" + NOME + r"|\d+))?)",
        base,
    )
    if not achado:
        return None
    tipo = texto[achado.start(1):achado.end(1)]
    return f"{tipo.capitalize()} {texto[achado.start(2):achado.end(2)]}"


def extrair_sugestoes(texto: str, hoje: date) -> dict:
    """Le a transcricao e devolve so os campos que conseguiu reconhecer."""
    if not texto:
        return {}
    contato_nome, contato_cargo = _extrair_contato(texto)
    data_retorno = _extrair_data_retorno(texto, hoje)
    sugestoes = {
        "nome_local": _extrair_nome_local(texto),
        "bairro": _extrair_depois_de(texto, r"\bbairro"),
        "cidade": _extrair_depois_de(texto, r"\bcidade"),
        "contato_nome": contato_nome,
        "contato_cargo": contato_cargo,
        "contato_telefone": _extrair_telefone(texto),
        "contato_email": _extrair_email(texto),
        "tipo_servico": _extrair_tipo_servico(texto),
        "qtd_postos": _extrair_qtd_postos(texto),
        "horarios": _extrair_horarios(texto),
        "valor_estimado": _extrair_valor(texto),
        "data_retorno": data_retorno.isoformat() if data_retorno else None,
    }
    return {campo: valor for campo, valor in sugestoes.items() if valor not in (None, "")}


# campo -> tamanho maximo (texto) ou None (numero/data); espelha VisitaComercial
CAMPOS_PREENCHIVEIS = {
    "nome_local": 200,
    "bairro": 100,
    "cidade": 100,
    "contato_nome": 150,
    "contato_cargo": 100,
    "contato_telefone": 50,
    "contato_email": 150,
    "tipo_servico": 50,
    "qtd_postos": None,
    "horarios": 300,
    "valor_estimado": None,
    "data_retorno": None,
}


def preencher_campos_vazios(visita: VisitaComercial, sugestoes: dict) -> list[str]:
    """Grava as sugestoes so nos campos que ainda estao vazios - nunca
    sobrescreve o que alguem digitou. Devolve os campos preenchidos."""
    preenchidos = []
    for campo, tamanho in CAMPOS_PREENCHIVEIS.items():
        valor = sugestoes.get(campo)
        if valor in (None, "") or getattr(visita, campo) not in (None, ""):
            continue
        if campo == "data_retorno":
            valor = date.fromisoformat(valor)
        elif tamanho is not None:
            valor = str(valor)[:tamanho]
        setattr(visita, campo, valor)
        preenchidos.append(campo)
    return preenchidos


# ---------------------------------------------------------------------------
# Jobs do agendador
# ---------------------------------------------------------------------------

def _hoje_brasilia() -> date:
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def transcrever_proximo_audio() -> bool:
    """Transcreve UM audio pendente (o mais antigo). Devolve True se
    processou algum. Roda em loop pelo job ate a fila esvaziar."""
    db = SessionLocal()
    try:
        agora = datetime.now(timezone.utc)
        orfaos = (
            db.query(VisitaComercialAudio)
            .filter(
                VisitaComercialAudio.status_transcricao == "processando",
                VisitaComercialAudio.transcricao_iniciada_em < agora - LIMITE_PROCESSANDO,
            )
            .all()
        )
        for audio in orfaos:
            audio.status_transcricao = "pendente"
        db.commit()

        audio = (
            db.query(VisitaComercialAudio)
            .filter(VisitaComercialAudio.status_transcricao == "pendente")
            .order_by(VisitaComercialAudio.criado_em)
            .first()
        )
        if audio is None:
            return False
        if not audio.arquivo_path or not os.path.exists(audio.arquivo_path):
            audio.status_transcricao = "erro"
            audio.erro_transcricao = "Arquivo de áudio não encontrado"
            db.commit()
            return True

        audio.status_transcricao = "processando"
        audio.transcricao_iniciada_em = agora
        db.commit()

        try:
            texto, duracao = transcrever_arquivo(audio.arquivo_path)
        except AudioLongoDemais:
            db.rollback()
            audio.status_transcricao = "erro"
            audio.erro_transcricao = f"Áudio com mais de {LIMITE_AUDIO_SEGUNDOS} segundos não é transcrito. Grave um áudio mais curto."
            db.commit()
            return True
        except Exception as erro:
            db.rollback()
            audio.status_transcricao = "erro"
            audio.erro_transcricao = "Não foi possível transcrever: o áudio parece corrompido ou num formato não reconhecido"
            db.commit()
            print("[audios] erro ao transcrever audio", audio.id, erro)
            return True

        sugestoes = extrair_sugestoes(texto, _hoje_brasilia())
        audio.transcricao = texto
        audio.duracao_segundos = duracao
        audio.sugestoes = sugestoes
        audio.campos_preenchidos = preencher_campos_vazios(audio.visita, sugestoes)
        audio.status_transcricao = "concluida"
        audio.erro_transcricao = None
        audio.transcrito_em = datetime.now(timezone.utc)
        db.commit()
        print("[audios] audio transcrito:", audio.id, "campos:", audio.campos_preenchidos)
        return True
    finally:
        db.close()


def transcrever_audios_pendentes() -> None:
    while transcrever_proximo_audio():
        pass


def apagar_audios_expirados() -> int:
    """Apaga o arquivo dos audios com mais de 48 horas; a transcricao fica."""
    db = SessionLocal()
    try:
        limite = datetime.now(timezone.utc) - timedelta(hours=HORAS_GUARDAR_AUDIO)
        audios = (
            db.query(VisitaComercialAudio)
            .filter(VisitaComercialAudio.arquivo_path.is_not(None), VisitaComercialAudio.criado_em < limite)
            .all()
        )
        for audio in audios:
            if os.path.exists(audio.arquivo_path):
                os.remove(audio.arquivo_path)
            audio.arquivo_path = None
            audio.audio_apagado_em = datetime.now(timezone.utc)
        db.commit()
        return len(audios)
    finally:
        db.close()
