"""
Corrige mais 20 clientes duplicados: mesma unidade real, mas cadastrada
duas vezes com nomes diferentes porque vieram de planilhas com
formatacao diferente. Move os horarios de servico E os chamados do
duplicado (sem CNPJ) para o cliente correto (com CNPJ), depois apaga
o duplicado.

Idempotente: se o duplicado ja nao existir mais (por ja ter sido
corrigido antes), so pula sem erro.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python corrigir_duplicados_clientes_v2.py
"""

from database import SessionLocal
from models import Chamado, Cliente, HorarioServico

# (nome do duplicado sem CNPJ, nome do cliente correto com CNPJ)
PARES_DUPLICADOS = [
    ("ALFA", "COLEGIO VISAO LTDA"),
    ("ASM", "AGORA SOU MAE LTDA"),
    ("CAMARA ANTONIO CARLOS", "CÂMARA MUNICIPAL DE ANTÔNIO CARLOS"),
    ("CANAL TELECOM", "CLOUD CANAL TECNOLOGIA LTDA"),
    ("CBA", "MERAKI JP EMPREENDIMENTO SPE LTDA"),
    ("CREDITO REAL", "COSTA ESMERALDA IMOVEIS LTDA"),
    ("EB ENERGY", "ENIO ANDRADE BRANCO"),
    ("ED. TRIANON", "COND. TRIANON"),
    ("GRALHA CAMPECHE", "GRALHA IMOVEIS - CAMPECHE"),
    ("HSTERN VILLA ROMANA", "HSJ COMERCIAL"),
    ("LCW MOTOS", "L.C.W. OFICINA DE VEICULOS LTDA"),
    ("LOFT", "X POWER IMPORTAÇÃO E EXPORTAÇÃO LTDA"),
    ("LPS", "LPS CONTABILIDADE LTDA"),
    ("MONT VERT", "MONTVERT RESIDENCIAL"),
    ("MPB", "MPB SANEAMENTOS LTDA"),
    ("NDTV", "SINERGY ND LTDA"),
    ("NPU", "NEC PLUS ULTRA GESTAO & TECNOLOGIA LTDA"),
    ("OSKLEN VILLA ROMANA", "BGJR VILLA ROMANA"),
    ("XP TI", "XPTI"),
    ("WAVE", "RESIDENCIAL WAVE"),
]


def normalizar(txt: str) -> str:
    return " ".join(txt.upper().strip().split())


def encontrar_cliente(db, nome_procurado: str):
    """Busca por nome, ignorando maiusculas/minusculas e espacos extras."""
    alvo = normalizar(nome_procurado)
    candidatos = [c for c in db.query(Cliente).all() if normalizar(c.nome) == alvo]
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        print(f"  atencao: '{nome_procurado}' bateu com mais de um cliente, pulando por seguranca")
    return None


def main():
    db = SessionLocal()
    try:
        total_horarios_migrados = 0
        total_chamados_migrados = 0
        total_clientes_apagados = 0
        total_nao_encontrados = 0

        for nome_duplicado, nome_correto in PARES_DUPLICADOS:
            duplicado = encontrar_cliente(db, nome_duplicado)
            correto = encontrar_cliente(db, nome_correto)

            if duplicado is None:
                print(f"pulando (duplicado nao encontrado, talvez ja corrigido): '{nome_duplicado}'")
                continue
            if correto is None:
                print(f"pulando (cliente correto nao encontrado): '{nome_correto}'")
                total_nao_encontrados += 1
                continue
            if duplicado.id == correto.id:
                print(f"pulando (ja e o mesmo registro): '{nome_duplicado}'")
                continue

            horarios = db.query(HorarioServico).filter_by(cliente_id=duplicado.id).all()
            for h in horarios:
                h.cliente_id = correto.id

            chamados = db.query(Chamado).filter_by(cliente_id=duplicado.id).all()
            for c in chamados:
                c.cliente_id = correto.id

            db.flush()

            detalhes = f"{len(horarios)} horario(s)"
            if chamados:
                detalhes += f", {len(chamados)} chamado(s)"
            print(f"'{nome_duplicado}' -> '{nome_correto}': {detalhes} migrados")

            total_horarios_migrados += len(horarios)
            total_chamados_migrados += len(chamados)

            db.delete(duplicado)
            total_clientes_apagados += 1

        db.commit()
        print("")
        print("Horarios migrados no total:", total_horarios_migrados)
        print("Chamados migrados no total:", total_chamados_migrados)
        print("Clientes duplicados apagados:", total_clientes_apagados)
        print("Pares nao encontrados:", total_nao_encontrados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
