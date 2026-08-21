"""
Cria a tabela horarios_servico e carrega o mapa de servicos real:
para cada colaborador, em quais dias/turnos ele atende qual cliente.

Cria automaticamente os clientes que apareciam no mapa mas ainda nao
estavam cadastrados (unidades de Posto Galo/Ale sem cadastro proprio,
e outros clientes que nao vieram na planilha de faturamento original).

Idempotente: pode rodar mais de uma vez sem duplicar horarios (embora
va pular quietamente os que ja existem, checando a combinacao completa).

COMO USAR
---------
Rode na VPS, dentro do container da aplicacao:
    docker compose exec app python migrar_mapa_servicos.py
"""

import models
from database import SessionLocal, engine
from models import Cliente, Colaborador, Empresa, HorarioServico

HORARIOS = [
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ADELAIDE FERREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. SÃO RAFAEL",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ADELAIDE FERREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "RES. MARACAIBO",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ADELAIDE FERREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. SÃO RAFAEL",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ADELAIDE FERREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "RES. MARACAIBO",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ADELAIDE FERREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. SÃO RAFAEL",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ADELAIDE FERREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "RES. MARACAIBO",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "CAMILIS DE SOUZA DIAS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "JOVI - V TECH MOBILE COMMUNICATION LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "CAMILIS DE SOUZA DIAS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "JOVI - V TECH MOBILE COMMUNICATION LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "CAMILIS DE SOUZA DIAS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "JOVI - V TECH MOBILE COMMUNICATION LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "CAMILIS DE SOUZA DIAS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "JOVI - V TECH MOBILE COMMUNICATION LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "CAMILIS DE SOUZA DIAS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "JOVI - V TECH MOBILE COMMUNICATION LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "18:00",
        "hora_fim": "00:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND. ARAUCARIA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "14:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "18:00",
        "hora_fim": "00:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "18:00",
        "hora_fim": "00:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "18:00",
        "hora_fim": "00:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND. ARAUCARIA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "14:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "18:00",
        "hora_fim": "00:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ELIZETE STREY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sabado",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER COSTA CARVALHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "PAULO (AUSTRIA)",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER COSTA CARVALHO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "EBP",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER COSTA CARVALHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CREFONO - CONSELHO REGIONAL DE FONOAUDIOLOGIA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER COSTA CARVALHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "PAULO (AUSTRIA)",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER COSTA CARVALHO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND VENEZIA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ESTER NASCIMENTO LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sabado",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "GRUPO ALMA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "GRUPO ALMA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "EVELLYN SANTOS OLIVEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "UNIFAEL",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "FABIANE DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "FABIANE DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "FABIANE DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "IGREJA METODISTA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "FABIANE DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "FABIANE DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "FABIANE DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "FABIANE DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "IGREJA METODISTA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "SAFE CONSIG TECNOLOGIA DA INFORMACAO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "ED. TRIANON",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "BOING AVIAMENTOS LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "SAFE CONSIG TECNOLOGIA DA INFORMACAO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "ED. TRIANON",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "BOING AVIAMENTOS LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "INVANCLEIA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "ED. TRIANON",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CANAL TELECOM",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND ED GRANITO",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "NDTV",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "NDTV",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CANAL TELECOM",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ISABEL CRISTINA PEREIRA DA SILVA SOUSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND ED GRANITO",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RENTEQ",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "KONICA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SELMA (Ed. Grasiela)",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RENTEQ",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "KONICA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SELMA (Ed. Grasiela)",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RENTEQ",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JESSICA CUNHA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "KONICA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "LUMMER ODONTOLOGIA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "INTERSTAR",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "LUMMER ODONTOLOGIA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "INTERSTAR",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "LUMMER ODONTOLOGIA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "INTERSTAR",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "LUMMER ODONTOLOGIA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "INTERSTAR",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "LUMMER ODONTOLOGIA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "INTERSTAR",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "JUCIENE CERQUEIRA MACHADO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "LUMMER ODONTOLOGIA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "16:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "16:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "16:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "16:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LILIANE BUENO PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SCITEC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "16:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "LUCIA MARIA DE SOUZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA DO SOCORRO ABREU BILBY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "RES PALMEIRAS",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA DO SOCORRO ABREU BILBY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "LPS",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA DO SOCORRO ABREU BILBY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "RES PALMEIRAS",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA DO SOCORRO ABREU BILBY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "RES PALMEIRAS",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA DO SOCORRO ABREU BILBY",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "ALFA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA IARA RODRIGUES VIEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DUFRY",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "10:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA IARA RODRIGUES VIEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DUFRY",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "16:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA IARA RODRIGUES VIEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "JUNG ACADEMIA DE GINASTICA LTDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA IARA RODRIGUES VIEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DUFRY",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "10:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA IARA RODRIGUES VIEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DUFRY",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "16:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "MARIA IARA RODRIGUES VIEIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DUFRY",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "NILSON VIVAN",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COND PRAIA COMPRIDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "RIVANIA HELENA DA SILVA PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CAMARA ANTONIO CARLOS",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "RIVANIA HELENA DA SILVA PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CAMARA ANTONIO CARLOS",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "RIVANIA HELENA DA SILVA PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CAMARA ANTONIO CARLOS",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "RIVANIA HELENA DA SILVA PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CAMARA ANTONIO CARLOS",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "RIVANIA HELENA DA SILVA PEREIRA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CAMARA ANTONIO CARLOS",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "ROSANGELA DE ARAUJO E SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "SAMARA DOS SANTOS ARAUJO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "MAZER",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "SAMARA DOS SANTOS ARAUJO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "MAZER",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "SAMARA DOS SANTOS ARAUJO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "MAZER",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "SAMARA DOS SANTOS ARAUJO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "MAZER",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "SAMARA DOS SANTOS ARAUJO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "MAZER",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "WALQUIRIA DE JESUS FRAZAO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DONA ROSA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "WALQUIRIA DE JESUS FRAZAO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "MARES DO SUL",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "WALQUIRIA DE JESUS FRAZAO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DONA ROSA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "WALQUIRIA DE JESUS FRAZAO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DONA ROSA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "CORDSUL",
        "colaborador_nome": "WALQUIRIA DE JESUS FRAZAO",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "MARES DO SUL",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA CARPES DUARTE",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "FRACTAL",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA CARPES DUARTE",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SKAYLINK LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA CARPES DUARTE",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ESCAMAX",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA CARPES DUARTE",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "BOTHOME ADVOGADOS",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA CARPES DUARTE",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SKAYLINK LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA CARPES DUARTE",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "BOTHOME ADVOGADOS",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA CARPES DUARTE",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "XP TI",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA SALETE CORREA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. VIDEIRA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA SALETE CORREA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. ARNO SCHEIDT",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA SALETE CORREA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. VIDEIRA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA SALETE CORREA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "13:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ANA SALETE CORREA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. VIDEIRA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TNS",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TERRA MARES",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "PHOTONITA LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "WAVETECH",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TNS",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TERRA MARES",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "PHOTONITA LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "WAVETECH",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TNS",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ARIANE MARTINS MOREIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TERRA MARES",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 ITACORUBI",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 ITACORUBI",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 TRINDADE",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 TRINDADE",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 ITACORUBI",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 ITACORUBI",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 TRINDADE",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 TRINDADE",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 ITACORUBI",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 ITACORUBI",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 TRINDADE",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "CLECI SALETE REES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 TRINDADE",
        "dia_semana": "sabado",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ATLANTIC GARDEN",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "EDIFICIO ALBATROZ",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "INOVA ANDAIMES",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "10:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CONDOMINIO MORADA DO SOL (BLOCO A)",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ATLANTIC GARDEN",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "EDIFICIO ALBATROZ",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CONDOMINIO MORADA DO SOL (BLOCO A)",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ATLANTIC GARDEN",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ELISETE ERTHAL TELLES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "EDIFICIO ALBATROZ",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "NEW HOTEL",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "NEW HOTEL",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ALKASOFT",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "15:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "NEW HOTEL",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "NEW HOTEL",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CAFÉ DO MERCADO",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "15:45",
        "hora_fim": "17:45"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "NEW HOTEL",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "08:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "GISELE TERIAGO DE LIZ ROSA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ALKASOFT",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "15:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COSTA AZUL",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COSTA AZUL",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "COSTA AZUL",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JANAINA SILVA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPERMERCADO FLORIPA - 3B MINI MERCADO E PADARIA LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CONDOMINIO RESIDENCIAL OLAVO BILAC",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CONDOMINIO EDIFICIO PRAIA DO RISO",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RESIDENCIAL LOURDES LIMA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CONDOMINIO RESIDENCIAL OLAVO BILAC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "COND. DANIELA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RESIDENCIAL LOURDES LIMA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CONDOMINIO EDIFICIO PRAIA DO RISO",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JAQUELINE REGINA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CONDOMINIO RESIDENCIAL OLAVO BILAC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CANTO DE CANASVIEIRAS",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "PORTONOVO",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CANTO DE CANASVIEIRAS",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "PORTONOVO",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CANTO DE CANASVIEIRAS",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "10:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOAO HENRIQUE CORREIA DE MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "PORTONOVO",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "JOELY DE MOURA SILVEIRA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "KEVIN FELIPE SOARES GONCALVES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "DONA DALMA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TRINIDAD E TOBAGO",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CONDOMINIO ROSANA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "DONA DALMA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TRINIDAD E TOBAGO",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "CONDOMINIO ROSANA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "DONA DALMA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LILIANE AMADO DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "TRINIDAD E TOBAGO",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LIVIA DE SOUZA ARAUJO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "23:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LIVIA DE SOUZA ARAUJO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "23:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LIVIA DE SOUZA ARAUJO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "23:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LIVIA DE SOUZA ARAUJO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "23:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LIVIA DE SOUZA ARAUJO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "23:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "LIVIA DE SOUZA ARAUJO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "10:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "NPU",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "11:00",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "NPU",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "11:00",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "NPU",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "11:00",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "NPU",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "11:00",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "NPU",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARGARETE CAPISTRANO MELO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "11:00",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARIA SALETE DA SILVA PARAVISI",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPER RIO - A3 SUPERMERCADO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARIA SALETE DA SILVA PARAVISI",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPER RIO - A3 SUPERMERCADO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARIA SALETE DA SILVA PARAVISI",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPER RIO - A3 SUPERMERCADO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARIA SALETE DA SILVA PARAVISI",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPER RIO - A3 SUPERMERCADO LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARIA SALETE DA SILVA PARAVISI",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPER RIO - A3 SUPERMERCADO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MARIA SALETE DA SILVA PARAVISI",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SUPER RIO - A3 SUPERMERCADO LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MIRELA REGINA COELHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "LEITURA VILLA ROMANA LIVRARIA E PAPELARIA LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MIRELA REGINA COELHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "OSKLEN VILLA ROMANA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MIRELA REGINA COELHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "LEITURA VILLA ROMANA LIVRARIA E PAPELARIA LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MIRELA REGINA COELHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "HSTERN VILLA ROMANA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "09:30",
        "hora_fim": "13:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "MIRELA REGINA COELHO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "LEITURA VILLA ROMANA LIVRARIA E PAPELARIA LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "NUBIA SENA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ZUCCHETTI SOFTWARE E SISTEMAS LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "NUBIA SENA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ZUCCHETTI SOFTWARE E SISTEMAS LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "NUBIA SENA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ZUCCHETTI SOFTWARE E SISTEMAS LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "NUBIA SENA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ZUCCHETTI SOFTWARE E SISTEMAS LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "NUBIA SENA DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ZUCCHETTI SOFTWARE E SISTEMAS LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSENICE DE JESUS DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSENICE DE JESUS DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSENICE DE JESUS DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSENICE DE JESUS DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSENICE DE JESUS DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SICREDI ESTREITO",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ROSIANE PEREIRA NUNES",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "SELMA DE BRITO FONSECA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "BENEVIX",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "15:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "SELMA DE BRITO FONSECA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "15:45",
        "hora_fim": "22:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "SELMA DE BRITO FONSECA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SECOVI",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "15:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "SELMA DE BRITO FONSECA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "15:45",
        "hora_fim": "22:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "SELMA DE BRITO FONSECA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "15:45",
        "hora_fim": "22:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "SELMA DE BRITO FONSECA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SONITEC",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "TEREZINHA VITÓRIO ROMÃO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VALDEMAR SEBASTIAO Res JANAINA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "TEREZINHA VITÓRIO ROMÃO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VALDEMAR SEBASTIAO Res GESSER",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "TEREZINHA VITÓRIO ROMÃO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VALDEMAR SEBASTIAO Res SOLANGE",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "TEREZINHA VITÓRIO ROMÃO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VALDEMAR SEBASTIAO Res JANAINA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "TEREZINHA VITÓRIO ROMÃO",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VALDEMAR SEBASTIAO Res GESSER",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "VERA REGINA GOUDEL",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SICOOB (COOPERATIVA DE CREDITO)",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "09:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "VERA REGINA GOUDEL",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "SICOOB (COOPERATIVA DE CREDITO)",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "09:30"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "KRETZER",
        "colaborador_nome": "ZENAIDE REIS DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ARMAZEM 3 JURERE",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ADILSON SOUSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ANTONIA CIRLENE DA SILVA PEREIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ASM",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VOX",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "INTERIP",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VOX",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "POSTO GALO LTDA - POT",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VOX",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "EB ENERGY",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VOX",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "INTERIP",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLAUDIA CRISTINA SANTIAGO DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "VOX",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:30",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "CLEONICE DO ROSARIO RIBEIRO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ELAINE CRISTINA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "ARC",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "11:15",
        "hora_fim": "13:15"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CRESCER DESENVOLVIMENTO INFANTIL LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CRESCER DESENVOLVIMENTO INFANTIL LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "HERONETE REGINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CRESCER DESENVOLVIMENTO INFANTIL LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANAINA CARDOSO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "SUA CIRURGIA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANAINA CARDOSO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "SUA CIRURGIA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANAINA CARDOSO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "SUA CIRURGIA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANAINA CARDOSO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "SUA CIRURGIA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANAINA CARDOSO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "SUA CIRURGIA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANE APARECIDA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANE APARECIDA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANE APARECIDA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANE APARECIDA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANE APARECIDA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JANE APARECIDA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BROGNOLI",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "KIKOS - KW FITNESS",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BROGNOLI",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BROGNOLI",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "KIKOS - KW FITNESS",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BROGNOLI",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BROGNOLI",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "JOSEANE CRISTINA VIEIRA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "KIKOS - KW FITNESS",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "KARLA ELZA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BUZZ",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "KARLA ELZA DA SILVA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "ACRONEX",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "10:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "KARLA ELZA DA SILVA",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "LIDER AVIAÇÃO",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "KARLA ELZA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BUZZ",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "KARLA ELZA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "MONT VERT",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "KARLA ELZA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "BUZZ",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "09:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "MILENA ARAUJO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "MILENA ARAUJO DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "DESBRAVADOR",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "MILENA ARAUJO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "FUFA-SC COMERCIO E REPRESENTACAO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "MILENA ARAUJO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "FUFA-SC COMERCIO E REPRESENTACAO LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "MILENA ARAUJO DOS SANTOS",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "DESBRAVADOR",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "MILENA ARAUJO DOS SANTOS",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "MOVAMI",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "PASSEIO DO LESTE",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "17:30",
        "hora_fim": "19:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "WAVE",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "MOVAMI",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "GMC",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "15:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "WAVE",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "MOVAMI",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "PASSEIO DO LESTE",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "17:30",
        "hora_fim": "19:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RANYELI RODRIGUES DE LIMA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "14:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "RENATA CRISTINA DE SOUZA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "13:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "13:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "13:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "13:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "13:00",
        "hora_fim": "16:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "17:00",
        "hora_fim": "21:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "ROSANGELA REGINA DE SOUZA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "DMI",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "HOYA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "PLATTANO",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "11:00",
        "hora_fim": "15:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CRTR - CONSELHO REGIONAL DE TECNICOS EM RADIOLOGIA DE SC",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "HOYA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CRTR - CONSELHO REGIONAL DE TECNICOS EM RADIOLOGIA DE SC",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "STAR SUL",
        "colaborador_nome": "SANDRA DO SOCORRO BARBOSA",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "HOYA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA ISABELLY JULIO COUTO BITTENCOURTT",
        "empresa_cliente": "FLC",
        "cliente_nome": "NULEUM LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA ISABELLY JULIO COUTO BITTENCOURTT",
        "empresa_cliente": "FLC",
        "cliente_nome": "NULEUM LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA ISABELLY JULIO COUTO BITTENCOURTT",
        "empresa_cliente": "FLC",
        "cliente_nome": "NULEUM LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA ISABELLY JULIO COUTO BITTENCOURTT",
        "empresa_cliente": "FLC",
        "cliente_nome": "NULEUM LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA ISABELLY JULIO COUTO BITTENCOURTT",
        "empresa_cliente": "FLC",
        "cliente_nome": "NULEUM LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA ISABELLY JULIO COUTO BITTENCOURTT",
        "empresa_cliente": "FLC",
        "cliente_nome": "NULEUM LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "MPB",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "EMPRESA DE CINEMAS ARCOPLEX S.A.",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. RICHARTZ",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "MPB",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "EMPRESA DE CINEMAS ARCOPLEX S.A.",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "MPB",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:00",
        "hora_fim": "11:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. RICHARTZ",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANA PAULA DOS SANTOS",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. COSTA DO MARFIM",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANGÉLICA DA TRINDADE MARIA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LOFT",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANGÉLICA DA TRINDADE MARIA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LOFT",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANGÉLICA DA TRINDADE MARIA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LOFT",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANGÉLICA DA TRINDADE MARIA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LOFT",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANGÉLICA DA TRINDADE MARIA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LOFT",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ANGÉLICA DA TRINDADE MARIA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LOFT",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "FLC",
        "cliente_nome": "MYTAPP TECNOLOGIA LTDA.",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "13:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ICPOL",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "15:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "FLC",
        "cliente_nome": "MYTAPP TECNOLOGIA LTDA.",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "13:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "FLC",
        "cliente_nome": "MYTAPP TECNOLOGIA LTDA.",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "13:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "ICPOL",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "15:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "FLC",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RESIDENCIAL ALVORADA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RESIDENCIAL ALVORADA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "FLC",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "DÉBORA SOUZA DE FRAYN",
        "empresa_cliente": "KRETZER",
        "cliente_nome": "RESIDENCIAL ALVORADA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "FLC",
        "cliente_nome": "CREDITO REAL",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "FLC",
        "cliente_nome": "CREDITO REAL",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "SUPERLEGAL ITAGUAÇU",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "CASA DO POVO",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "18:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "FLC",
        "cliente_nome": "CREDITO REAL",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "09:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "ELAINE CRISTINA DE JESUS RODRIGUES",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:30",
        "hora_fim": "17:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "GABRIELLY ALFA BATISTA",
        "empresa_cliente": "FLC",
        "cliente_nome": "MANAGER CONSULTORIA EM INFORMATICA LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "GABRIELLY ALFA BATISTA",
        "empresa_cliente": "FLC",
        "cliente_nome": "MANAGER CONSULTORIA EM INFORMATICA LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "GABRIELLY ALFA BATISTA",
        "empresa_cliente": "FLC",
        "cliente_nome": "MANAGER CONSULTORIA EM INFORMATICA LTDA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "GABRIELLY ALFA BATISTA",
        "empresa_cliente": "FLC",
        "cliente_nome": "MANAGER CONSULTORIA EM INFORMATICA LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "GABRIELLY ALFA BATISTA",
        "empresa_cliente": "FLC",
        "cliente_nome": "MANAGER CONSULTORIA EM INFORMATICA LTDA",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JAQUELINE MARIANA CUNHA DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LUMIX HEALTHCARE LTDA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JAQUELINE MARIANA CUNHA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JAQUELINE MARIANA CUNHA DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LUMIX HEALTHCARE LTDA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JAQUELINE MARIANA CUNHA DA SILVA",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "RES. ELDORADO",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JAQUELINE MARIANA CUNHA DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "LUMIX HEALTHCARE LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "11:30",
        "hora_fim": "14:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "11:30",
        "hora_fim": "14:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "11:30",
        "hora_fim": "14:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "11:30",
        "hora_fim": "14:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "06:30",
        "hora_fim": "10:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JOÃO VITOR SANTOS OLIVEIRA",
        "empresa_cliente": "FLC",
        "cliente_nome": "CBA",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "11:30",
        "hora_fim": "14:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JUSSARA NUNES",
        "empresa_cliente": "FLC",
        "cliente_nome": "GRALHA NOVO CAMPECHE",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "09:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JUSSARA NUNES",
        "empresa_cliente": "FLC",
        "cliente_nome": "GRALHA CAMPECHE",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JUSSARA NUNES",
        "empresa_cliente": "FLC",
        "cliente_nome": "GRALHA NOVO CAMPECHE",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "09:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JUSSARA NUNES",
        "empresa_cliente": "FLC",
        "cliente_nome": "GRALHA CAMPECHE",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JUSSARA NUNES",
        "empresa_cliente": "CORDSUL",
        "cliente_nome": "CONFIDENCE - VILLA ROMANA",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:30",
        "hora_fim": "12:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JUSSARA NUNES",
        "empresa_cliente": "FLC",
        "cliente_nome": "GRALHA NOVO CAMPECHE",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "09:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "JUSSARA NUNES",
        "empresa_cliente": "FLC",
        "cliente_nome": "GRALHA CAMPECHE",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "FLC",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "FLC",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "FLC",
        "cliente_nome": "GALPAO BG",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "FLC",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "STAR SUL",
        "cliente_nome": "POSTO GALO LTDA",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "07:30",
        "hora_fim": "11:30"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "KARINE SANTOS DA SILVA NASCIMENTO",
        "empresa_cliente": "FLC",
        "cliente_nome": "POSTO ALE (unidades diversas)",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "13:00",
        "hora_fim": "17:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "LUCIMERY CHAGAS RIBEIRO",
        "empresa_cliente": "FLC",
        "cliente_nome": "LCW MOTOS",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "LUCIMERY CHAGAS RIBEIRO",
        "empresa_cliente": "FLC",
        "cliente_nome": "LCW MOTOS",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "LUCIMERY CHAGAS RIBEIRO",
        "empresa_cliente": "FLC",
        "cliente_nome": "LCW MOTOS",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "LUCIMERY CHAGAS RIBEIRO",
        "empresa_cliente": "FLC",
        "cliente_nome": "LCW MOTOS",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "LUCIMERY CHAGAS RIBEIRO",
        "empresa_cliente": "FLC",
        "cliente_nome": "LCW MOTOS",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "segunda",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "segunda",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "terca",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "terca",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "quarta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "quarta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "quinta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "quinta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "sexta",
        "turno": "manha",
        "hora_inicio": "08:00",
        "hora_fim": "12:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "sexta",
        "turno": "tarde",
        "hora_inicio": "12:15",
        "hora_fim": "14:15"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "sabado",
        "turno": "manha",
        "hora_inicio": "06:00",
        "hora_fim": "10:00"
    },
    {
        "empresa_colaborador": "FLC",
        "colaborador_nome": "SOLANGE COELHO DA SILVA",
        "empresa_cliente": "FLC",
        "cliente_nome": "COND. BELMAR",
        "dia_semana": "sabado",
        "turno": "tarde",
        "hora_inicio": "10:15",
        "hora_fim": "12:15"
    }
]

def main():
    models.HorarioServico.__table__.create(engine, checkfirst=True)
    print("Tabela horarios_servico OK (criada ou ja existente)")

    db = SessionLocal()
    try:
        empresas_por_nome = {e.nome: e for e in db.query(Empresa).all()}

        total_clientes_criados = 0
        total_horarios_criados = 0
        total_horarios_existentes = 0
        colaboradores_nao_encontrados = set()

        cache_clientes = {}  # (empresa_nome, cliente_nome) -> Cliente

        for h in HORARIOS:
            empresa_colab = empresas_por_nome.get(h["empresa_colaborador"])
            if empresa_colab is None:
                continue

            colaborador = (
                db.query(Colaborador)
                .filter_by(empresa_id=empresa_colab.id, nome=h["colaborador_nome"])
                .first()
            )
            if colaborador is None:
                colaboradores_nao_encontrados.add((h["empresa_colaborador"], h["colaborador_nome"]))
                continue

            empresa_cliente = empresas_por_nome.get(h["empresa_cliente"])
            if empresa_cliente is None:
                continue

            chave_cliente = (h["empresa_cliente"], h["cliente_nome"])
            cliente = cache_clientes.get(chave_cliente)
            if cliente is None:
                cliente = (
                    db.query(Cliente)
                    .filter_by(empresa_id=empresa_cliente.id, nome=h["cliente_nome"])
                    .first()
                )
                if cliente is None:
                    cliente = Cliente(empresa_id=empresa_cliente.id, nome=h["cliente_nome"])
                    db.add(cliente)
                    db.flush()
                    total_clientes_criados += 1
                cache_clientes[chave_cliente] = cliente

            ja_existe = (
                db.query(HorarioServico)
                .filter_by(
                    colaborador_id=colaborador.id,
                    cliente_id=cliente.id,
                    dia_semana=h["dia_semana"],
                    turno=h["turno"],
                )
                .first()
            )
            if ja_existe:
                total_horarios_existentes += 1
                continue

            db.add(
                HorarioServico(
                    colaborador_id=colaborador.id,
                    cliente_id=cliente.id,
                    dia_semana=h["dia_semana"],
                    turno=h["turno"],
                    hora_inicio=h["hora_inicio"],
                    hora_fim=h["hora_fim"],
                )
            )
            total_horarios_criados += 1

        db.commit()

        print("")
        print("Clientes novos criados:", total_clientes_criados)
        print("Horarios de servico criados:", total_horarios_criados)
        print("Horarios ja existentes (pulados):", total_horarios_existentes)
        if colaboradores_nao_encontrados:
            print("Colaboradores nao encontrados no banco (pulados):", len(colaboradores_nao_encontrados))
            for e, n in sorted(colaboradores_nao_encontrados):
                print("  -", e, n)
    finally:
        db.close()


if __name__ == "__main__":
    main()
