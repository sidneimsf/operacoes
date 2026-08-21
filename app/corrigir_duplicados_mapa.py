"""
Corrige 7 clientes duplicados que o mapa de servicos criou sem perceber
que ja existia um cadastro equivalente (com CNPJ) vindo da planilha de
faturamento. Move os horarios de servico do duplicado (sem CNPJ) para
o cliente correto (com CNPJ), depois apaga o duplicado.

Pares tratados (achados por nome identico ou claramente correspondente
em uma auditoria manual - os casos sem correspondencia clara, como
"COND. ARNO SCHEIDT", "COND. COSTA DO MARFIM" e "COND. RICHARTZ",
foram propositalmente deixados de fora e continuam como estao).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python corrigir_duplicados_mapa.py
"""

from database import SessionLocal
from models import Cliente, HorarioServico

# (nome do duplicado sem CNPJ, nome do cliente correto com CNPJ)
PARES_DUPLICADOS = [
    ("ARMAZEM 3 ITACORUBI", "ARMAZEM ITACORUBI - MINI MERCADO ITACORUBI LTDA"),
    ("ARMAZEM 3 JURERE", "ARMAZEM JURERE - 3B MINI MERCADO E PADARIA LTDA"),
    ("ARMAZEM 3 TRINDADE", "ARMAZEM TRINDADE - B&S MINI MERCADO E PADARIA LTDA"),
    ("COND. ARAUCARIA", "CONDOMINIO EDIFICIO RESIDENCIAL ARAUCARIA"),
    ("COND. DANIELA", "CONDOMINIO EDIFICIO DANIELA"),
    ("COND. VIDEIRA", "CONDOMINIO EDIFICIO RESIDENCIAL VIDEIRA"),
    ("COND. BELMAR", "EDIFICIO RESIDENCIAL E COMERCIAL BELMAR"),
]


def main():
    db = SessionLocal()
    try:
        total_horarios_migrados = 0
        total_clientes_apagados = 0

        for nome_duplicado, nome_correto in PARES_DUPLICADOS:
            duplicado = db.query(Cliente).filter_by(nome=nome_duplicado).first()
            correto = db.query(Cliente).filter_by(nome=nome_correto).first()

            if duplicado is None:
                print(f"pulando (duplicado nao encontrado): {nome_duplicado}")
                continue
            if correto is None:
                print(f"pulando (correto nao encontrado): {nome_correto}")
                continue

            horarios = db.query(HorarioServico).filter_by(cliente_id=duplicado.id).all()
            for h in horarios:
                h.cliente_id = correto.id
            db.flush()

            print(f"'{nome_duplicado}' -> '{nome_correto}': {len(horarios)} horarios migrados")
            total_horarios_migrados += len(horarios)

            db.delete(duplicado)
            total_clientes_apagados += 1

        db.commit()
        print("")
        print("Horarios migrados no total:", total_horarios_migrados)
        print("Clientes duplicados apagados:", total_clientes_apagados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
