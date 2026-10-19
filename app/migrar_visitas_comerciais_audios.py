"""
Cria a tabela visitas_comerciais_audios - audios gravados nas visitas
comerciais, com a transcricao feita na propria VPS. O arquivo de audio
some depois de 30 dias; a transcricao fica.

Idempotente: pode rodar mais de uma vez sem problema.

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_visitas_comerciais_audios.py
"""

import models
from database import engine


def main():
    models.VisitaComercialAudio.__table__.create(engine, checkfirst=True)
    print("Tabela visitas_comerciais_audios OK (criada ou ja existente)")


if __name__ == "__main__":
    main()
