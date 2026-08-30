import os
from datetime import date

from sqlalchemy.orm import Session

from email_alertas import enviar_email
from models import CustoDiario, Usuario


def buscar_custos_pendentes(db: Session) -> list[CustoDiario]:
    """Custos ainda nao incluidos em nenhum e-mail de reembolso."""
    return (
        db.query(CustoDiario)
        .filter(CustoDiario.notificado.is_(False))
        .order_by(CustoDiario.data.asc())
        .all()
    )


def montar_corpo_email(custos: list[CustoDiario]) -> str:
    linhas = ""
    total = 0.0
    for c in custos:
        total += c.valor
        linhas += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #333;">{c.usuario.nome}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c.tipo}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c.data.strftime('%d/%m/%Y')}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">R$ {c.valor:.2f}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c.nome_beneficiario or c.usuario.nome}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c.chave_pix or '—'}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{c.descricao or '—'}</td>
          <td style="padding:8px;border-bottom:1px solid #333;">{'Em anexo' if c.comprovante_path else 'Sem comprovante'}</td>
        </tr>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; color: #222;">
      <h2>Custos diários para reembolso</h2>
      <p>Os custos abaixo foram lançados pelos supervisores e aguardam reembolso manual:</p>
      <table style="border-collapse: collapse; width: 100%;">
        <thead>
          <tr style="background:#eee;">
            <th style="padding:8px;text-align:left;">Quem lançou</th>
            <th style="padding:8px;text-align:left;">Tipo</th>
            <th style="padding:8px;text-align:left;">Data</th>
            <th style="padding:8px;text-align:left;">Valor</th>
            <th style="padding:8px;text-align:left;">Reembolsar para</th>
            <th style="padding:8px;text-align:left;">Chave PIX</th>
            <th style="padding:8px;text-align:left;">Observação</th>
            <th style="padding:8px;text-align:left;">Comprovante</th>
          </tr>
        </thead>
        <tbody>
          {linhas}
        </tbody>
      </table>
      <p style="margin-top:14px;"><strong>Total a reembolsar: R$ {total:.2f}</strong></p>
      <p style="color:#888;font-size:12px;margin-top:20px;">E-mail automatico do sistema de operações do Grupo Star Sul.</p>
    </div>
    """


def destinatarios_reembolso() -> list[str]:
    bruto = os.environ.get("REEMBOLSO_EMAILS", "")
    return [e.strip() for e in bruto.split(",") if e.strip()]


def verificar_e_enviar_custos(db: Session) -> dict:
    """
    Roda a checagem e envia o e-mail de reembolso se houver custo
    pendente. Retorna um resumo (usado tanto pelo agendador automatico
    quanto por um botao de teste manual).
    """
    custos = buscar_custos_pendentes(db)

    if not custos:
        return {"enviado": False, "motivo": "Nenhum custo pendente de notificação", "total": 0}

    destinatarios = destinatarios_reembolso()
    if not destinatarios:
        return {"enviado": False, "motivo": "Nenhum destinatario configurado (REEMBOLSO_EMAILS)", "total": len(custos)}

    valor_total = sum(c.valor for c in custos)
    assunto = f"[Grupo Star Sul - Operações] {len(custos)} custo(s) para reembolso - R$ {valor_total:.2f}"
    corpo = montar_corpo_email(custos)

    anexos = [
        (c.comprovante_path, c.comprovante_nome_original or f"comprovante_{c.id}")
        for c in custos
        if c.comprovante_path
    ]

    enviar_email(destinatarios, assunto, corpo, anexos=anexos)

    for c in custos:
        c.notificado = True
    db.commit()

    return {"enviado": True, "destinatarios": destinatarios, "total": len(custos), "valor_total": valor_total}
