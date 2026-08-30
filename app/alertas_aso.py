import os
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from email_alertas import enviar_email
from models import Colaborador, ColaboradorEvento

DIAS_ANTECEDENCIA_ALERTA = 7


def buscar_asos_criticos(db: Session) -> list[dict]:
    """
    Pega o ASO mais recente de cada colaborador (pelo data_fim mais alto)
    e retorna os que estao vencidos ou vencendo em ate 7 dias.
    """
    subquery = (
        db.query(
            ColaboradorEvento.colaborador_id,
            func.max(ColaboradorEvento.data_fim).label("data_fim_max"),
        )
        .filter(ColaboradorEvento.tipo == "aso", ColaboradorEvento.data_fim.isnot(None))
        .group_by(ColaboradorEvento.colaborador_id)
        .subquery()
    )

    eventos = (
        db.query(ColaboradorEvento)
        .join(
            subquery,
            (ColaboradorEvento.colaborador_id == subquery.c.colaborador_id)
            & (ColaboradorEvento.data_fim == subquery.c.data_fim_max),
        )
        .filter(ColaboradorEvento.tipo == "aso")
        .all()
    )

    hoje = date.today()
    limite = hoje + timedelta(days=DIAS_ANTECEDENCIA_ALERTA)
    criticos = []

    for e in eventos:
        if e.data_fim is None or e.data_fim > limite:
            continue
        colaborador = db.get(Colaborador, e.colaborador_id)
        if colaborador is None or colaborador.status == "desligado":
            continue
        dias_restantes = (e.data_fim - hoje).days
        criticos.append(
            {
                "colaborador_nome": colaborador.nome,
                "empresa_nome": colaborador.empresa.nome,
                "data_exame": e.data_inicio,
                "data_vencimento": e.data_fim,
                "dias_restantes": dias_restantes,
            }
        )

    criticos.sort(key=lambda x: x["dias_restantes"])
    return criticos


def montar_corpo_email(criticos: list[dict]) -> str:
    linhas = ""
    for c in criticos:
        status = "VENCIDO" if c["dias_restantes"] < 0 else f"vence em {c['dias_restantes']} dia(s)"
        cor = "#e2574c" if c["dias_restantes"] < 0 else "#e8a33d"
        linhas += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #333;">{c['colaborador_nome']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c['empresa_nome']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c['data_vencimento'].strftime('%d/%m/%Y')}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:{cor};font-weight:bold;">{status}</td>
        </tr>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; color: #222;">
      <h2>Alerta de ASOs vencendo</h2>
      <p>Os colaboradores abaixo estao com o ASO (exame ocupacional) vencido ou vencendo nos proximos {DIAS_ANTECEDENCIA_ALERTA} dias:</p>
      <table style="border-collapse: collapse; width: 100%;">
        <thead>
          <tr style="background:#eee;">
            <th style="padding:8px;text-align:left;">Colaborador</th>
            <th style="padding:8px;text-align:left;">Empresa</th>
            <th style="padding:8px;text-align:left;">Vencimento</th>
            <th style="padding:8px;text-align:left;">Status</th>
          </tr>
        </thead>
        <tbody>
          {linhas}
        </tbody>
      </table>
      <p style="color:#888;font-size:12px;margin-top:20px;">E-mail automatico do sistema de operações do Grupo Star Sul.</p>
    </div>
    """


def destinatarios_alerta() -> list[str]:
    bruto = os.environ.get("ALERTA_ASO_EMAILS", "")
    return [e.strip() for e in bruto.split(",") if e.strip()]


def verificar_e_enviar_alertas(db: Session) -> dict:
    """
    Roda a checagem e envia o e-mail se houver algo critico.
    Retorna um resumo do que aconteceu (usado tanto pelo agendador
    automatico quanto pelo botao de teste manual).
    """
    criticos = buscar_asos_criticos(db)

    if not criticos:
        return {"enviado": False, "motivo": "Nenhum ASO vencido ou vencendo em breve", "total": 0}

    destinatarios = destinatarios_alerta()
    if not destinatarios:
        return {"enviado": False, "motivo": "Nenhum destinatario configurado (ALERTA_ASO_EMAILS)", "total": len(criticos)}

    assunto = f"[Grupo Star Sul - Operações] {len(criticos)} ASO(s) vencido(s) ou vencendo em breve"
    corpo = montar_corpo_email(criticos)
    enviar_email(destinatarios, assunto, corpo)

    return {"enviado": True, "destinatarios": destinatarios, "total": len(criticos)}
