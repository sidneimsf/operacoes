import os

from sqlalchemy.orm import Session

from crm_saude import calcular_saude_carteira, formatar_moeda
from email_alertas import enviar_email


def montar_corpo_email(em_risco: list[dict], contratos: list[tuple[dict, dict]]) -> str:
    linhas_risco = ""
    for l in em_risco:
        motivos = "<br>".join(m["texto"] for m in l["motivos"][:3])
        linhas_risco += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #ddd;"><b>{l['cliente_nome']}</b><br><span style="color:#888;font-size:12px;">{l['empresa_nome']} · {l['supervisor_nome'] or 'sem supervisor'}</span></td>
          <td style="padding:8px;border-bottom:1px solid #ddd;color:#c13327;font-weight:bold;">{l['score']}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd;font-size:13px;">{motivos}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd;font-size:13px;">{l['acao_sugerida']}</td>
        </tr>
        """

    linhas_contrato = ""
    for l, a in contratos:
        valor = (l["contrato"] or {}).get("valor_mensal")
        linhas_contrato += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #ddd;">{l['cliente_nome']}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd;">{a['texto']}</td>
          <td style="padding:8px;border-bottom:1px solid #ddd;">{formatar_moeda(valor) + '/mês' if valor else '—'}</td>
        </tr>
        """

    secao_risco = ""
    if em_risco:
        secao_risco = f"""
      <h3>Clientes em risco ({len(em_risco)})</h3>
      <table style="border-collapse: collapse; width: 100%;">
        <thead><tr style="background:#eee;">
          <th style="padding:8px;text-align:left;">Cliente</th>
          <th style="padding:8px;text-align:left;">Nota</th>
          <th style="padding:8px;text-align:left;">Por quê</th>
          <th style="padding:8px;text-align:left;">Próxima ação</th>
        </tr></thead>
        <tbody>{linhas_risco}</tbody>
      </table>
        """

    secao_contratos = ""
    if contratos:
        secao_contratos = f"""
      <h3>Contratos que pedem ação ({len(contratos)})</h3>
      <table style="border-collapse: collapse; width: 100%;">
        <thead><tr style="background:#eee;">
          <th style="padding:8px;text-align:left;">Cliente</th>
          <th style="padding:8px;text-align:left;">Situação</th>
          <th style="padding:8px;text-align:left;">Valor</th>
        </tr></thead>
        <tbody>{linhas_contrato}</tbody>
      </table>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; color: #222;">
      <h2>Resumo semanal do CRM</h2>
      <p>Clientes que precisam de atenção esta semana, segundo a nota de saúde do CRM
      (reclamações, visitas, postos vagos, trocas de colaborador, faltas e satisfação),
      e contratos com vencimento ou reajuste próximos.</p>
      {secao_risco}
      {secao_contratos}
      <p style="color:#888;font-size:12px;margin-top:20px;">E-mail automatico do sistema de operações do Grupo Star Sul. Detalhes completos no menu CRM.</p>
    </div>
    """


def destinatarios_alerta() -> list[str]:
    bruto = os.environ.get("ALERTA_CRM_EMAILS", "")
    return [e.strip() for e in bruto.split(",") if e.strip()]


def verificar_e_enviar_crm(db: Session) -> dict:
    linhas = calcular_saude_carteira(db)
    em_risco = sorted((l for l in linhas if l["faixa"] == "risco"), key=lambda l: l["score"])
    contratos = [(l, a) for l in linhas for a in l["alertas_contrato"] if a["urgencia"] == "alta"]
    contratos.sort(key=lambda x: x[1]["dias"])

    if not em_risco and not contratos:
        return {"enviado": False, "motivo": "Nenhum cliente em risco nem contrato pedindo acao", "total": 0}

    destinatarios = destinatarios_alerta()
    total = len(em_risco) + len(contratos)
    if not destinatarios:
        return {"enviado": False, "motivo": "Nenhum destinatario configurado (ALERTA_CRM_EMAILS)", "total": total}

    assunto = (f"[Grupo Star Sul - CRM] {len(em_risco)} cliente(s) em risco e "
               f"{len(contratos)} contrato(s) pedindo ação")
    enviar_email(destinatarios, assunto, montar_corpo_email(em_risco, contratos))
    return {"enviado": True, "destinatarios": destinatarios, "total": total}
