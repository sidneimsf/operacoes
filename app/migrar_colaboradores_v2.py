"""
Recria a tabela colaboradores com o novo formato (empresa, cargo,
contato, admissao, supervisor, status) e carrega os 87 colaboradores
reais extraidos da planilha de RH.

ATENCAO: apaga o que estiver na tabela colaboradores antes de recriar.
Isso e seguro porque a tabela esta vazia em producao ate agora - nenhum
colaborador real foi cadastrado ainda por outro caminho.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_colaboradores_v2.py
"""

import models
from database import SessionLocal, engine
from models import Colaborador, Empresa, Usuario

EMPRESAS_COLABORADORES = {
    "CORDSUL": [
        {
            "registro": "118",
            "nome": "ROSANGELA DE ARAUJO E SILVA",
            "cargo": "SERVENTE DE SERVIÇOS GERAIS",
            "contato": "98451-9261",
            "admissao": "2018-11-19",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "156",
            "nome": "MARILDA BARBOSA PETIT FRERE",
            "cargo": "SERVENTE DE SERVIÇOS GERAIS",
            "contato": "98828-1185",
            "admissao": "2019-10-08",
            "supervisor_raw": "Afastada"
        },
        {
            "registro": "175",
            "nome": "LILIANE BUENO PEREIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "93300-7291",
            "admissao": "2020-10-15",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "179",
            "nome": "FABIANA MACHADO MENEZES",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98474-3040",
            "admissao": "2021-01-15",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "195",
            "nome": "ELENICE MACHADO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99626-7482",
            "admissao": "2021-07-26",
            "supervisor_raw": "Afastada"
        },
        {
            "registro": "243",
            "nome": "JUCIENE CERQUEIRA MACHADO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98837-9978",
            "admissao": "2022-08-12",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "251",
            "nome": "LUCIA MARIA DE SOUZA DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98446-9613",
            "admissao": "2022-12-01",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "265",
            "nome": "ADELAIDE FERREIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98846-8484",
            "admissao": "2023-03-10",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "271",
            "nome": "ESTER COSTA CARVALHO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98867-4779",
            "admissao": "2023-04-04",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "278",
            "nome": "ESTER NASCIMENTO LIMA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98860-8634",
            "admissao": "2023-07-12",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "283",
            "nome": "WALQUIRIA DE JESUS FRAZAO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98421-8754",
            "admissao": "2023-09-01",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "289",
            "nome": "FABIANE DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98817-2276",
            "admissao": "2023-10-06",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "313",
            "nome": "RODRIGO RANGEL FERREIRA",
            "cargo": "SUPERVISOR OPERACIONAL",
            "contato": "98864-3148",
            "admissao": "2024-09-23",
            "supervisor_raw": "Administrativo"
        },
        {
            "registro": "316",
            "nome": "MARIA DO SOCORRO ABREU BILBY",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99945-2493",
            "admissao": "2024-12-12",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "317",
            "nome": "JULIANA DE JESUS DOS PASSOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99180-4743",
            "admissao": "2024-12-19",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "324",
            "nome": "CAROLINE MEDEIROS",
            "cargo": "GERENTE GERAL",
            "contato": "98444-4939",
            "admissao": "2025-02-24",
            "supervisor_raw": "Administrativo"
        },
        {
            "registro": "329",
            "nome": "JESSICA CUNHA DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98879-1145",
            "admissao": "2025-04-23",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "339",
            "nome": "MARIA IARA RODRIGUES VIEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99190-8733",
            "admissao": "2025-09-24",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "344",
            "nome": "ELIZETE STREY",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98463-8668",
            "admissao": "2025-12-05",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "346",
            "nome": "RIVANIA HELENA DA SILVA PEREIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98492-9651",
            "admissao": "2026-01-06",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "347",
            "nome": "INVANCLEIA DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99640-3953",
            "admissao": "2026-02-02",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "348",
            "nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99820-1704",
            "admissao": "2026-03-23",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "349",
            "nome": "EVELLYN SANTOS OLIVEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "(71) 8885-6696",
            "admissao": "2026-05-11",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "350",
            "nome": "NILSON VIVAN",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98423-0129",
            "admissao": "2026-05-14",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "351",
            "nome": "CAMILIS DE SOUZA DIAS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98866-0431",
            "admissao": "2026-07-24",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "352",
            "nome": "SAMARA DOS SANTOS ARAUJO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "(91) 98512-4830",
            "admissao": "2026-08-10",
            "supervisor_raw": "Rodrigo"
        }
    ],
    "KRETZER": [
        {
            "registro": "6",
            "nome": "VERA REGINA GOUDEL",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98496-0005",
            "admissao": "2019-10-21",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "24",
            "nome": "ELISETE ERTHAL TELLES",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99688-8192",
            "admissao": "2020-12-21",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "25",
            "nome": "TEREZINHA VITÓRIO ROMÃO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98494-3816",
            "admissao": "2021-01-14",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "30",
            "nome": "GISELE TERIAGO DE LIZ ROSA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98458-5093",
            "admissao": "2021-03-10",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "35",
            "nome": "ANA SALETE CORREA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98485-5685 / 99829-9466",
            "admissao": "2021-07-01",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "36",
            "nome": "ANA CARPES DUARTE",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98837-7666",
            "admissao": "2021-08-02",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "64",
            "nome": "TATIANE VIEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98466-5910",
            "admissao": "2022-09-01",
            "supervisor_raw": "Afastada"
        },
        {
            "registro": "66",
            "nome": "ROSENICE DE JESUS DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98467-6829",
            "admissao": "2022-09-02",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "68",
            "nome": "ROSIANE PEREIRA NUNES",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98409-9763",
            "admissao": "2022-09-26",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "108",
            "nome": "JOZELI TEREZINHA LOPES DE OLIVEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99639-9615",
            "admissao": "2024-09-11",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "121",
            "nome": "KEVIN FELIPE SOARES GONCALVES",
            "cargo": "OFICIAL DE MANUTENÇÃO PREDIAL",
            "contato": "99161-9860",
            "admissao": "2024-12-03",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "143",
            "nome": "JOAO HENRIQUE CORREIA DE MELO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98461-7586",
            "admissao": "2025-07-11",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "151",
            "nome": "CLECI SALETE REES",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98823-0698",
            "admissao": "2025-09-24",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "156",
            "nome": "JOELY DE MOURA SILVEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "(55) 9178-0121",
            "admissao": "2025-11-03",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "162",
            "nome": "JAQUELINE REGINA DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98802-4106",
            "admissao": "2026-02-02",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "166",
            "nome": "LUCIANA LUANA FERREIRA FIDELIS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99989-3556",
            "admissao": "2026-02-11",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "169",
            "nome": "SANDRA APARECIDA DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99939-9775",
            "admissao": "2026-03-18",
            "supervisor_raw": "Administrativo"
        },
        {
            "registro": "170",
            "nome": "NUBIA SENA DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99643-5719",
            "admissao": "2026-04-09",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "171",
            "nome": "MARGARETE CAPISTRANO MELO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99115-5354",
            "admissao": "2026-04-14",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "174",
            "nome": "ARIANE MARTINS MOREIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "(51) 99805-4758",
            "admissao": "2026-04-22",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "175",
            "nome": "ZENAIDE REIS DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99634-4503",
            "admissao": "2026-04-29",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "176",
            "nome": "LILIANE AMADO DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "7400-9058",
            "admissao": "2026-04-30",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "178",
            "nome": "LIVIA DE SOUZA ARAUJO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "9973-8607",
            "admissao": "2026-06-23",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "179",
            "nome": "JANAINA SILVA DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "(83) 99386-7795",
            "admissao": "2026-07-03",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "180",
            "nome": "MARIA SALETE DA SILVA PARAVISI",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "9968-8821",
            "admissao": "2026-07-09",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "181",
            "nome": "SELMA DE BRITO FONSECA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98803-7577",
            "admissao": "2026-08-13",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "182",
            "nome": "MIRELA REGINA COELHO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "48985095429",
            "admissao": "2026-08-18",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "30",
            "nome": "IRACENE ROCHA DE JESUS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "48-996865671",
            "admissao": "2026-08-20",
            "supervisor_raw": "Sandra"
        }
    ],
    "STAR SUL": [
        {
            "registro": "16",
            "nome": "ROSANGELA REGINA DE SOUZA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98496-2609",
            "admissao": "2023-10-11",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "36",
            "nome": "ISLA AZEVEDO DOS SANTOS",
            "cargo": "ASSISTENTE ADMINISTRATIVO",
            "contato": "(75) 99247-2071",
            "admissao": "2024-04-01",
            "supervisor_raw": "Administrativo"
        },
        {
            "registro": "41",
            "nome": "SANDRA DO SOCORRO BARBOSA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "(91) 98966-3297",
            "admissao": "2024-05-14",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "51",
            "nome": "KARLA ELZA DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "48 9812-6817",
            "admissao": "2024-09-02",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "54",
            "nome": "RANYELI RODRIGUES DE LIMA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99165-5660",
            "admissao": "2024-09-27",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "56",
            "nome": "CLEONICE DO ROSARIO RIBEIRO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98850-3569",
            "admissao": "2024-11-01",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "70",
            "nome": "JANAINA CARDOSO DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98466-1599",
            "admissao": "2025-03-31",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "72",
            "nome": "JESSICA MACHADO DA CONCEICAO",
            "cargo": "SUPERVISORA DE RH",
            "contato": "98852-2535",
            "admissao": "2025-04-09",
            "supervisor_raw": "Administrativo"
        },
        {
            "registro": "77",
            "nome": "RENATA CRISTINA DE SOUZA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99979-3893",
            "admissao": "2025-05-27",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "106",
            "nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98472-6916",
            "admissao": "2025-11-21",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "110",
            "nome": "ELAINE CRISTINA DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99952-6155",
            "admissao": "2025-12-18",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "120",
            "nome": "JANE APARECIDA VIEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98877-4161",
            "admissao": "2026-04-01",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "123",
            "nome": "JOSEANE CRISTINA VIEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99624-0863",
            "admissao": "2026-04-13",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "125",
            "nome": "MARILUCIA MARIA MACHADO GONCALVES",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98461-8954",
            "admissao": "2026-04-30",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "126",
            "nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "(91) 9221-2928",
            "admissao": "2026-05-14",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "128",
            "nome": "MILENA ARAUJO DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "9936-6171",
            "admissao": "2026-05-19",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "130",
            "nome": "INGRID DEGERING",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98841-2508",
            "admissao": "2026-07-21",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "132",
            "nome": "ADILSON SOUSA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99613-7256",
            "admissao": "2026-08-13",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "133",
            "nome": "HERONETE REGINA VIEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99216-0012",
            "admissao": "2026-08-13",
            "supervisor_raw": "Sandra"
        }
    ],
    "FLC": [
        {
            "registro": "23",
            "nome": "ANA PAULA DOS SANTOS",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98859-2744",
            "admissao": "2026-07-01",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "2",
            "nome": "BEATRIZ ANDRADE",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99957-2241",
            "admissao": "2026-02-11",
            "supervisor_raw": "Afastada"
        },
        {
            "registro": "7",
            "nome": "LUCIMERY CHAGAS RIBEIRO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99190-9879",
            "admissao": "2026-03-10",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "10",
            "nome": "JUSSARA NUNES",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99886-7785",
            "admissao": "2026-04-01",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "14",
            "nome": "SOLANGE COELHO DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99198-1314",
            "admissao": "2026-05-02",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "16",
            "nome": "KARINE SANTOS DA SILVA NASCIMENTO",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99818-5727",
            "admissao": "2026-05-08",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "19",
            "nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98463-7775",
            "admissao": "2026-06-01",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "21",
            "nome": "JEHNNIFER ISABEL DA ROSA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99149-6221",
            "admissao": "2026-06-11",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "22",
            "nome": "ANGÉLICA DA TRINDADE MARIA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98431-6832",
            "admissao": "2026-06-26",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "24",
            "nome": "GABRIELLY ALFA BATISTA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99828-7287",
            "admissao": "2026-07-03",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "25",
            "nome": "JAQUELINE MARIANA CUNHA DA SILVA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98494-8229",
            "admissao": "2026-07-17",
            "supervisor_raw": "Rodrigo"
        },
        {
            "registro": "27",
            "nome": "DÉBORA SOUZA DE FRAYN",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "99950-1871",
            "admissao": "2026-07-24",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "28",
            "nome": "ANA ISABELLY JULIO COUTO BITTENCOURTT",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "98841-1594",
            "admissao": "2026-08-06",
            "supervisor_raw": "Sandra"
        },
        {
            "registro": "29",
            "nome": "JOÃO VITOR SANTOS OLIVEIRA",
            "cargo": "AUXILIAR DE SERVIÇOS GERAIS",
            "contato": "71-984835120",
            "admissao": "2026-08-18",
            "supervisor_raw": "Sandra"
        }
    ]
}

def main():
    print("Recriando as tabelas colaboradores e colaborador_eventos com o novo formato...")
    if engine.dialect.has_table(engine.connect(), "horarios_servico"):
        models.HorarioServico.__table__.drop(engine, checkfirst=True)
    models.ColaboradorEvento.__table__.drop(engine, checkfirst=True)
    models.Colaborador.__table__.drop(engine, checkfirst=True)
    models.Colaborador.__table__.create(engine, checkfirst=True)
    models.ColaboradorEvento.__table__.create(engine, checkfirst=True)
    print("Tabelas recriadas.")

    db = SessionLocal()
    try:
        supervisores_por_nome = {
            u.nome: u.id
            for u in db.query(Usuario).filter_by(papel="supervisor", ativo=True).all()
        }
        empresas_por_nome = {e.nome: e.id for e in db.query(Empresa).all()}

        total_criados = 0
        total_empresas_nao_encontradas = set()

        for nome_empresa, colaboradores in EMPRESAS_COLABORADORES.items():
            empresa_id = empresas_por_nome.get(nome_empresa)
            if empresa_id is None:
                total_empresas_nao_encontradas.add(nome_empresa)
                continue

            for dados in colaboradores:
                supervisor_raw = dados.get("supervisor_raw")
                supervisor_id = supervisores_por_nome.get(supervisor_raw)
                status = "afastado" if supervisor_raw == "Afastada" else "ativo"

                admissao = None
                if dados.get("admissao"):
                    from datetime import date
                    admissao = date.fromisoformat(dados["admissao"])

                colaborador = Colaborador(
                    empresa_id=empresa_id,
                    registro=dados.get("registro"),
                    nome=dados["nome"],
                    cargo=dados.get("cargo"),
                    contato=dados.get("contato"),
                    data_admissao=admissao,
                    supervisor_id=supervisor_id,
                    status=status,
                )
                db.add(colaborador)
                total_criados += 1

        db.commit()
        print("")
        print("Colaboradores criados:", total_criados)
        if total_empresas_nao_encontradas:
            print("ATENCAO - empresas nao encontradas no banco:", total_empresas_nao_encontradas)
    finally:
        db.close()


if __name__ == "__main__":
    main()
