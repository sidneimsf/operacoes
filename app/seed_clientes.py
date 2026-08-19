"""
Povoa o banco com as empresas e clientes reais, extraidos da planilha
de movimentacao de cobranca. Idempotente: pode rodar mais de uma vez
sem duplicar nada (usa nome da empresa e nome do cliente como chave).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python seed_clientes.py
"""

from database import SessionLocal
from models import Cliente, Empresa

EMPRESAS_CLIENTES = {
    "CORDSUL": [
        "SKAYLINK LTDA",
        "HOYA",
        "HDL DA AMAZONIA",
        "EDP",
        "PASSEIO DO LESTE",
        "HSJ COMERCIAL",
        "JUNG ACADEMIA DE GINASTICA LTDA",
        "SUPERLEGAL ITAGUAÇU",
        "SUPERLEGAL VIACATARINA",
        "SUPERLEGAL BEIRAMAR",
        "XPTI",
        "EBP",
        "TDSA",
        "COOPERCOMPANY",
        "ACRONEX",
        "VAEES",
        "JOVI - V TECH MOBILE COMMUNICATION LTDA",
        "GMC",
        "CONFIDENCE - VILLA ROMANA",
        "CONFIDENCE TRAVELEX - BEIRAMAR",
        "DUFRY",
        "LUMMER ODONTOLOGIA",
        "MAZER",
        "CONDOMINIO RESIDENCIAL ITAPOA",
        "SICREDI ESTREITO",
        "MARES DO SUL",
        "SEGWARE",
        "PLATTANO",
        "GALERIA (SELITO)",
        "COND VENEZIA",
        "SELMA (Ed. Grasiela)",
        "BGJR FLORIPA BEIRAMAR",
        "COSTA ESMERALDA IMOVEIS LTDA",
        "DMI",
        "SCITEC",
        "CLOUD CANAL TECNOLOGIA LTDA",
        "RES PALMEIRAS",
        "RES. MARACAIBO",
        "COND ED GRANITO",
        "VILLA BORGHESE",
        "LPS CONTABILIDADE LTDA",
        "CONDOMINIO EDIFICIO PRAIA DO RISO",
        "DONA ROSA",
        "COND. TRIANON",
        "COND PRAIA COMPRIDA",
        "COSTA AZUL",
        "CRTR - CONSELHO REGIONAL DE TECNICOS EM RADIOLOGIA DE SC",
        "CÂMARA MUNICIPAL DE ANTÔNIO CARLOS",
        "UNIFAEL",
        "COLEGIO VISAO LTDA"
    ],
    "KRETZER": [
        "NATURA",
        "ICPOL",
        "CREFONO - CONSELHO REGIONAL DE FONOAUDIOLOGIA",
        "RESIDENCIAL ALVORADA",
        "PHOTONITA LTDA",
        "INOVA ANDAIMES",
        "FRACTAL",
        "MOUT’S SOLUÇÕES",
        "ZUCCHETTI SOFTWARE E SISTEMAS LTDA",
        "LEITURA VILLA ROMANA LIVRARIA E PAPELARIA LTDA",
        "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA",
        "ARMAZEM TRINDADE - B&S MINI MERCADO E PADARIA LTDA",
        "ARMAZEM ITACORUBI - MINI MERCADO ITACORUBI LTDA",
        "ARMAZEM JURERE - 3B MINI MERCADO E PADARIA LTDA",
        "SUPER RIO - A3 SUPERMERCADO LTDA",
        "WAVETECH",
        "SECOVI",
        "BOTHOME ADVOGADOS",
        "BENEVIX",
        "SICOOB (COOPERATIVA DE CREDITO)",
        "LIDER AVIAÇÃO",
        "VOX",
        "SICREDI INGLESES",
        "AREIAS BRANCAS",
        "PORTONOVO",
        "NEC PLUS ULTRA GESTAO & TECNOLOGIA LTDA",
        "RESIDENCIAL LOURDES LIMA",
        "CONDOMINIO ROSANA",
        "DESBRAVADOR",
        "ALKASOFT",
        "TERRA MARES",
        "CANTO DE CANASVIEIRAS",
        "RESIDENCIAL GUATTARI",
        "CONDOMINIO RESIDENCIAL OLAVO BILAC",
        "CONDOMINIO EDIFICIO RESIDENCIAL ARAUCARIA",
        "SOLAR DAS AMENDOEIRAS",
        "BDO",
        "TNS",
        "ALEMAO JURERE - STERTZ MATERIAIS DE CONSTRUCAO LTDA",
        "TRINIDAD E TOBAGO",
        "RENTEQ",
        "PAULO (AUSTRIA)",
        "VALDEMAR SEBASTIAO Res JANAINA",
        "VALDEMAR SEBASTIAO Res GESSER",
        "VALDEMAR SEBASTIAO Res SOLANGE",
        "COND. SÃO RAFAEL",
        "CONDOMINIO EDIFICIO DANIELA",
        "ATLANTIC GARDEN",
        "CONDOMINIO MORADA DO SOL (BLOCO A)",
        "CONDOMINIO MORADA DO SOL (BLOCO B)",
        "EDIFICIO ALBATROZ",
        "SONITEC MULHER",
        "SONITEC",
        "RESIDENCIAL SARAH"
    ],
    "STAR SUL": [
        "KONICA",
        "BUSCO",
        "RES. ELDORADO",
        "INTERIP",
        "ARC",
        "CRESCER DESENVOLVIMENTO INFANTIL LTDA",
        "AGORA SOU MAE LTDA",
        "NEW HOTEL",
        "CASA DO POVO",
        "CAFÉ DO MERCADO",
        "ED. GIRASSOL",
        "KIKOS - KW FITNESS",
        "ESCAMAX",
        "UNO CLINICA",
        "AVILA COMERCIO DE COMBUSTIVEIS LTDA",
        "POSTO GALO LTDA",
        "AUTO POSTO VIADUTO LTDA",
        "IGREJA METODISTA",
        "MOVAMI",
        "MONTVERT RESIDENCIAL",
        "ENIO ANDRADE BRANCO",
        "FUFA-SC COMERCIO E REPRESENTACAO LTDA",
        "ROBOX",
        "BGJR VILLA ROMANA",
        "BROGNOLI",
        "SUA CIRURGIA",
        "MONACO",
        "DONA DALMA"
    ],
    "FLC": [
        "SINERGY ND LTDA",
        "MAX INCORPORAÇÕES",
        "BOING AVIAMENTOS LTDA",
        "MARQUINHO COMBUSTIVEIS E SERVICOS LTDA",
        "AC COMERCIO DE COMBUSTIVEIS LTDA",
        "MARQUINHO COMBUSTIVEIS E TRANSPORTES LTDA",
        "POSTO GALO LTDA - POT",
        "ADOTESC",
        "SALVIA SAUDE CORPORATIVA",
        "L.C.W. OFICINA DE VEICULOS LTDA",
        "EMPRESA DE CINEMAS ARCOPLEX S.A.",
        "SPACCIO - POLESELLO E VUELMA ALIMENTOS LTDA",
        "RESIDENCIAL WAVE",
        "X POWER IMPORTAÇÃO E EXPORTAÇÃO LTDA",
        "GRALHA IMOVEIS - JURERE",
        "GRALHA IMOVEIS - CAMPECHE",
        "EDIFICIO VILLAGE BLEU RESIDENCE NAUTIQUE",
        "MERAKI JP EMPREENDIMENTO SPE LTDA",
        "CONDOMINIO EDIFICIO RESIDENCIAL VIDEIRA",
        "LWART SOLUÇÕES AMBIENTAIS S.A.",
        "EDIFICIO RESIDENCIAL E COMERCIAL BELMAR",
        "MANAGER CONSULTORIA EM INFORMATICA LTDA",
        "MAKERHERO LTDA",
        "SAFE CONSIG TECNOLOGIA DA INFORMACAO LTDA",
        "MPB SANEAMENTOS LTDA",
        "LUMIX HEALTHCARE LTDA",
        "MYTAPP TECNOLOGIA LTDA.",
        "NULEUM LTDA"
    ]
}

def main():
    db = SessionLocal()
    try:
        total_empresas_criadas = 0
        total_clientes_criados = 0
        total_clientes_existentes = 0

        for nome_empresa, clientes in EMPRESAS_CLIENTES.items():
            empresa = db.query(Empresa).filter_by(nome=nome_empresa).first()
            if empresa is None:
                empresa = Empresa(nome=nome_empresa)
                db.add(empresa)
                db.flush()  # garante empresa.id disponivel antes dos clientes
                total_empresas_criadas += 1
                print("empresa criada:", nome_empresa)

            for nome_cliente in clientes:
                existe = (
                    db.query(Cliente)
                    .filter_by(empresa_id=empresa.id, nome=nome_cliente)
                    .first()
                )
                if existe:
                    total_clientes_existentes += 1
                    continue
                db.add(Cliente(empresa_id=empresa.id, nome=nome_cliente))
                total_clientes_criados += 1

        db.commit()
        print("")
        print("Empresas criadas:", total_empresas_criadas)
        print("Clientes criados:", total_clientes_criados)
        print("Clientes ja existentes (pulados):", total_clientes_existentes)
    finally:
        db.close()


if __name__ == "__main__":
    main()
