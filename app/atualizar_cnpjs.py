"""
Preenche o CNPJ dos clientes ja cadastrados, casando por empresa + nome.
Idempotente: pode rodar mais de uma vez sem problema, so atualiza o
campo cnpj (nao cria nem duplica clientes).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python atualizar_cnpjs.py
"""

from database import SessionLocal
from models import Cliente, Empresa

EMPRESAS_CNPJS = {
    "CORDSUL": {
        "SKAYLINK LTDA": "09.500.535/0001-04",
        "HOYA": "68.571.041/0018-10",
        "HDL DA AMAZONIA": "04.034.304/0004-73",
        "EDP": "04.149.295/0005-47",
        "PASSEIO DO LESTE": "31.136.503/0001-12",
        "HSJ COMERCIAL": "02.091.365/0082-60",
        "JUNG ACADEMIA DE GINASTICA LTDA": "41.767.206/0001-29",
        "SUPERLEGAL ITAGUAÇU": "03.733.595/0038-74",
        "SUPERLEGAL VIACATARINA": "03.733.595/0041-70",
        "SUPERLEGAL BEIRAMAR": "03.733.595/0029-83",
        "XPTI": "18.190.216/0001-22",
        "EBP": "08.839.940/0001-80",
        "TDSA": "07.803.583/0001-38",
        "COOPERCOMPANY": "52.042.661/0002-64",
        "ACRONEX": "20.252.840/0002-30",
        "VAEES": "21.052.140/0001-83",
        "JOVI - V TECH MOBILE COMMUNICATION LTDA": "54.911.018/0006-89",
        "GMC": "09.534.555/0001-98",
        "CONFIDENCE - VILLA ROMANA": "04.913.129/0109-61",
        "CONFIDENCE TRAVELEX - BEIRAMAR": "04.913.129/0035-90",
        "DUFRY": "17.625.216/0050-23",
        "LUMMER ODONTOLOGIA": "46.941.285/0001-66",
        "MAZER": "94.623.741/0004-15",
        "CONDOMINIO RESIDENCIAL ITAPOA": "09.627.341/0001-66",
        "SICREDI ESTREITO": "87.795.639/0027-28",
        "MARES DO SUL": "08.996.305/0001-07",
        "SEGWARE": "04.570.566/0001-00",
        "PLATTANO": "27.839.811/0001-37",
        "GALERIA (SELITO)": "245.439.859-15",
        "COND VENEZIA": "18.240.145/0001-25",
        "SELMA (Ed. Grasiela)": "444.649.169-53",
        "BGJR FLORIPA BEIRAMAR": "41.605.657/0001-60",
        "COSTA ESMERALDA IMOVEIS LTDA": "48.460.746/0001-04",
        "DMI": "02.202.456/0001-60",
        "SCITEC": "10.228.279/0001-19",
        "CLOUD CANAL TECNOLOGIA LTDA": "56.479.699/0001-79",
        "RES PALMEIRAS": "72.197.767/0001-63",
        "RES. MARACAIBO": "85.209.609/0001-28",
        "COND ED GRANITO": "00.434.162/0001-38",
        "VILLA BORGHESE": "07.547.819/0001-12",
        "LPS CONTABILIDADE LTDA": "72.390.586/0001-59",
        "CONDOMINIO EDIFICIO PRAIA DO RISO": "81.617.722/0001-91",
        "DONA ROSA": "09.423.904/0001-02",
        "COND. TRIANON": "79.887.717/0001-57",
        "COND PRAIA COMPRIDA": "82.101.593/0001-47",
        "COSTA AZUL": "01.559.879/0001-79",
        "CRTR - CONSELHO REGIONAL DE TECNICOS EM RADIOLOGIA DE SC": "83.159.541/0001-94",
        "CÂMARA MUNICIPAL DE ANTÔNIO CARLOS": "07.409.010/0001-24",
        "UNIFAEL": "04.986.320/0083-60",
        "COLEGIO VISAO LTDA": "07.622.613/0001-00"
    },
    "KRETZER": {
        "NATURA": "24.276.833/0023-53",
        "ICPOL": "32.659.057/0001-93",
        "CREFONO - CONSELHO REGIONAL DE FONOAUDIOLOGIA": "73.392.409/0001-74",
        "RESIDENCIAL ALVORADA": "83.159.616/0001-37",
        "PHOTONITA LTDA": "05.013.932/0001-92",
        "INOVA ANDAIMES": "14.790.651/0001-37",
        "FRACTAL": "12.958.626/0001-94",
        "MOUT’S SOLUÇÕES": "25.056.849/0001-08",
        "ZUCCHETTI SOFTWARE E SISTEMAS LTDA": "03.916.076/0004-00",
        "LEITURA VILLA ROMANA LIVRARIA E PAPELARIA LTDA": "53.624.422/0001-02",
        "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA": "55.293.000/0003-80",
        "ARMAZEM TRINDADE - B&S MINI MERCADO E PADARIA LTDA": "54.649.817/0001-14",
        "ARMAZEM ITACORUBI - MINI MERCADO ITACORUBI LTDA": "55.303.590/0001-13",
        "ARMAZEM JURERE - 3B MINI MERCADO E PADARIA LTDA": "55.293.000/0001-19",
        "SUPER RIO - A3 SUPERMERCADO LTDA": "48.030.121/0001-02",
        "WAVETECH": "15.565.869/0001-50",
        "SECOVI": "00.440.037/0001-30",
        "BOTHOME ADVOGADOS": "02.492.252/0001-00",
        "BENEVIX": "11.073.058/0001-81",
        "SICOOB (COOPERATIVA DE CREDITO)": "37.079.720/0002-85",
        "LIDER AVIAÇÃO": "17.162.579/0018-30",
        "VOX": "05.954.407/0001-71",
        "SICREDI INGLESES": "87.795.639/0023-02",
        "AREIAS BRANCAS": "02.737.408/0001-76",
        "PORTONOVO": "08.170.572/0001-20",
        "NEC PLUS ULTRA GESTAO & TECNOLOGIA LTDA": "02.067.638/0001-75",
        "RESIDENCIAL LOURDES LIMA": "03.236.611/0001-21",
        "CONDOMINIO ROSANA": "95.815.429/0001-43",
        "DESBRAVADOR": "82.176.983/0006-90",
        "ALKASOFT": "00.146.825/0001-19",
        "TERRA MARES": "11.582.361/0001-00",
        "CANTO DE CANASVIEIRAS": "00.651.702/0001-35",
        "RESIDENCIAL GUATTARI": "10.621.232/0001-10",
        "CONDOMINIO RESIDENCIAL OLAVO BILAC": "80.674.229/0001-40",
        "CONDOMINIO EDIFICIO RESIDENCIAL ARAUCARIA": "03.671.797/0001-47",
        "SOLAR DAS AMENDOEIRAS": "07.322.200/0001-00",
        "BDO": "54.276.936/0009-26",
        "TNS": "10.574.882/0001-52",
        "ALEMAO JURERE - STERTZ MATERIAIS DE CONSTRUCAO LTDA": "01.429.308/0001-10",
        "TRINIDAD E TOBAGO": "02.703.284/0001-08",
        "RENTEQ": "80.756.182/0001-64",
        "PAULO (AUSTRIA)": "385.468.419-34",
        "VALDEMAR SEBASTIAO Res JANAINA": "246.200.689-34",
        "VALDEMAR SEBASTIAO Res GESSER": "246.200.689-34",
        "VALDEMAR SEBASTIAO Res SOLANGE": "246.200.689-34",
        "COND. SÃO RAFAEL": "81.577.546/0001-01",
        "CONDOMINIO EDIFICIO DANIELA": "82.701.921/0001-46",
        "ATLANTIC GARDEN": "06.921.752/0001-71",
        "CONDOMINIO MORADA DO SOL (BLOCO A)": "05.655.656/0001-66",
        "CONDOMINIO MORADA DO SOL (BLOCO B)": "07.009.639/0001-87",
        "EDIFICIO ALBATROZ": "85.209.906/0001-73",
        "SONITEC MULHER": "81.553.042/0001-51",
        "SONITEC": "81.553.042/0002-32",
        "RESIDENCIAL SARAH": "05.514.483/0001-66"
    },
    "STAR SUL": {
        "KONICA": "23.022.114/0006-42",
        "BUSCO": "29.461.751/0001-97",
        "RES. ELDORADO": "31.028.427/0001-21",
        "INTERIP": "18.220.100/0001-99",
        "ARC": "01.565.706/0001-63",
        "CRESCER DESENVOLVIMENTO INFANTIL LTDA": "344.625.860/001-28",
        "AGORA SOU MAE LTDA": "16.624.250/0002-13",
        "NEW HOTEL": "01.432.935/0001-00",
        "CASA DO POVO": "83.715.003/0003-09",
        "CAFÉ DO MERCADO": "05.345.804/0003-08",
        "ED. GIRASSOL": "08.669.501/0001-77",
        "KIKOS - KW FITNESS": "05.013.773/0026-84",
        "ESCAMAX": "24.845.692/0007-22",
        "UNO CLINICA": "24.287.253/0001-56",
        "AVILA COMERCIO DE COMBUSTIVEIS LTDA": "01.401.005/0001-99",
        "POSTO GALO LTDA": "81.326.258/0012-37",
        "AUTO POSTO VIADUTO LTDA": "04.308.884/0001-05",
        "IGREJA METODISTA": "03.530.820/0054-95",
        "MOVAMI": "28.403.305/0007-59",
        "MONTVERT RESIDENCIAL": "62.550.244/0001-03",
        "ENIO ANDRADE BRANCO": "33.976.434/0001-80",
        "FUFA-SC COMERCIO E REPRESENTACAO LTDA": "07.164.711/0001-40",
        "ROBOX": "21.960.725/0001-00",
        "BGJR VILLA ROMANA": "35.643.566/0001-16",
        "BROGNOLI": "61.861.493/0001-49",
        "SUA CIRURGIA": "48.401.656/0001-42",
        "MONACO": "14.152.853/0001-53",
        "DONA DALMA": "79.005.773/0001-10"
    },
    "FLC": {
        "SINERGY ND LTDA": "47.825.093/0001-57",
        "MAX INCORPORAÇÕES": "11.249.827/0001-50",
        "BOING AVIAMENTOS LTDA": "04.822.558/0001-03",
        "MARQUINHO COMBUSTIVEIS E SERVICOS LTDA": "05.991.479/0003-50",
        "AC COMERCIO DE COMBUSTIVEIS LTDA": "08.356.325/0001-13",
        "MARQUINHO COMBUSTIVEIS E TRANSPORTES LTDA": "86.916.889/0001-77",
        "POSTO GALO LTDA - POT": "81.326.258/0032-80",
        "ADOTESC": "83.469.254/0001-80",
        "SALVIA SAUDE CORPORATIVA": "36.933.494/0001-04",
        "L.C.W. OFICINA DE VEICULOS LTDA": "04.472.318/0001-26",
        "EMPRESA DE CINEMAS ARCOPLEX S.A.": "17.040.988/0031-30",
        "SPACCIO - POLESELLO E VUELMA ALIMENTOS LTDA": "44.796.133/0001-91",
        "RESIDENCIAL WAVE": "65.564.617/0001-85",
        "X POWER IMPORTAÇÃO E EXPORTAÇÃO LTDA": "11.147.460/0001-63",
        "GRALHA IMOVEIS - JURERE": "18.091.083/0006-41",
        "GRALHA IMOVEIS - CAMPECHE": "18.091.083/0005-60",
        "EDIFICIO VILLAGE BLEU RESIDENCE NAUTIQUE": "55.529.659/0001-21",
        "MERAKI JP EMPREENDIMENTO SPE LTDA": "47.505.762/0001-03",
        "CONDOMINIO EDIFICIO RESIDENCIAL VIDEIRA": "81.348.526/0001-69",
        "LWART SOLUÇÕES AMBIENTAIS S.A.": "46.201.083/0017-45",
        "EDIFICIO RESIDENCIAL E COMERCIAL BELMAR": "10.798.989/0001-84",
        "MANAGER CONSULTORIA EM INFORMATICA LTDA": "80.750.714/0001-56",
        "MAKERHERO LTDA": "12.672.380/0001-90",
        "SAFE CONSIG TECNOLOGIA DA INFORMACAO LTDA": "21.935.427/0001-51",
        "MPB SANEAMENTOS LTDA": "78.221.066/0001-07",
        "LUMIX HEALTHCARE LTDA": "48.146.804/0002-00",
        "MYTAPP TECNOLOGIA LTDA.": "21.718.627/0001-52",
        "NULEUM LTDA": "66.196.085/0001-33"
    }
}

def main():
    db = SessionLocal()
    try:
        total_atualizados = 0
        total_nao_encontrados = 0

        for nome_empresa, clientes_cnpj in EMPRESAS_CNPJS.items():
            empresa = db.query(Empresa).filter_by(nome=nome_empresa).first()
            if empresa is None:
                print("empresa nao encontrada (pulando):", nome_empresa)
                continue

            for nome_cliente, cnpj in clientes_cnpj.items():
                cliente = (
                    db.query(Cliente)
                    .filter_by(empresa_id=empresa.id, nome=nome_cliente)
                    .first()
                )
                if cliente is None:
                    print("cliente nao encontrado (pulando):", nome_empresa, "-", nome_cliente)
                    total_nao_encontrados += 1
                    continue
                cliente.cnpj = cnpj
                total_atualizados += 1

        db.commit()
        print("")
        print("CNPJs atualizados:", total_atualizados)
        print("Clientes nao encontrados:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
