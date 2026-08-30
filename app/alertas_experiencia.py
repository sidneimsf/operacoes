from datetime import date, timedelta

from sqlalchemy.orm import Session

from email_alertas import enviar_email
from models import Colaborador

DIAS_ANTECEDENCIA_ALERTA = 7


def buscar_experiencias_criticas(db: Session) -> list[dict]:
    """
    Colaboradores ativos com o checkpoint de 30 ou 90 dias vencendo em
    ate 7 dias (ou ja vencido). Cada um pode aparecer 1 ou 2 vezes na
    lista, se os dois checkpoints estiverem proximos ao mesmo tempo.
    """
    hoje = date.today()
    limite = hoje + timedelta(days=DIAS_ANTECEDENCIA_ALERTA)

    colaboradores = (
        db.query(Colaborador)
        .filter(Colaborador.status != "desligado")
        .filter(
            (Colaborador.data_fim_experiencia_30.isnot(None) & (Colaborador.data_fim_experiencia_30 <= limite))
            | (Colaborador.data_fim_experiencia_90.isnot(None) & (Colaborador.data_fim_experiencia_90 <= limite))
        )
        .all()
    )

    criticos = []
    for c in colaboradores:
        if c.data_fim_experiencia_30 and c.data_fim_experiencia_30 <= limite:
            criticos.append(
                {
                    "colaborador_nome": c.nome,
                    "empresa_nome": c.empresa.nome,
                    "checkpoint": "30 dias",
                    "data_checkpoint": c.data_fim_experiencia_30,
                    "dias_restantes": (c.data_fim_experiencia_30 - hoje).days,
                }
            )
        if c.data_fim_experiencia_90 and c.data_fim_experiencia_90 <= limite:
            criticos.append(
                {
                    "colaborador_nome": c.nome,
                    "empresa_nome": c.empresa.nome,
                    "checkpoint": "90 dias",
                    "data_checkpoint": c.data_fim_experiencia_90,
                    "dias_restantes": (c.data_fim_experiencia_90 - hoje).days,
                }
            )

    criticos.sort(key=lambda x: x["dias_restantes"])
    return criticos


def montar_corpo_email(criticos: list[dict]) -> str:
    linhas = ""
    for c in criticos:
        status_txt = "VENCIDO" if c["dias_restantes"] < 0 else f"em {c['dias_restantes']} dia(s)"
        cor = "#e2574c" if c["dias_restantes"] < 0 else "#e8a33d"
        linhas += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #333;">{c['colaborador_nome']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c['empresa_nome']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c['checkpoint']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c['data_checkpoint'].strftime('%d/%m/%Y')}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:{cor};font-weight:bold;">{status_txt}</td>
        </tr>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; color: #222;">
      <h2>Colaboradores em fim de período de experiência</h2>
      <p>Os colaboradores abaixo estão chegando (ou já passaram) num checkpoint de experiência (30 ou 90 dias).
      É hora de decidir se a empresa vai continuar com eles:</p>
      <table style="border-collapse: collapse; width: 100%;">
        <thead>
          <tr style="background:#eee;">
            <th style="padding:8px;text-align:left;">Colaborador</th>
            <th style="padding:8px;text-align:left;">Empresa</th>
            <th style="padding:8px;text-align:left;">Checkpoint</th>
            <th style="padding:8px;text-align:left;">Data</th>
            <th style="padding:8px;text-align:left;">Situação</th>
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
    import os

    bruto = os.environ.get("ALERTA_EXPERIENCIA_EMAILS", "")
    return [e.strip() for e in bruto.split(",") if e.strip()]


def verificar_e_enviar_experiencias(db: Session) -> dict:
    criticos = buscar_experiencias_criticas(db)

    if not criticos:
        return {"enviado": False, "motivo": "Nenhum checkpoint de experiência vencido ou vencendo em breve", "total": 0}

    destinatarios = destinatarios_alerta()
    if not destinatarios:
        return {"enviado": False, "motivo": "Nenhum destinatario configurado (ALERTA_EXPERIENCIA_EMAILS)", "total": len(criticos)}

    assunto = f"[Grupo Star Sul - Operações] {len(criticos)} colaborador(es) em fim de período de experiência"
    corpo = montar_corpo_email(criticos)
    enviar_email(destinatarios, assunto, corpo)

    return {"enviado": True, "destinatarios": destinatarios, "total": len(criticos)}
