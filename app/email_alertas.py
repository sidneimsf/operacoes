import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def smtp_configurado() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def enviar_email(destinatarios: list[str], assunto: str, corpo_html: str) -> None:
    """
    Envia um e-mail via SMTP, usando as credenciais configuradas no .env.
    Lanca excecao se o SMTP nao estiver configurado ou o envio falhar -
    quem chama decide como tratar isso (logar, devolver erro na API, etc).
    """
    if not smtp_configurado():
        raise RuntimeError(
            "SMTP nao configurado. Defina SMTP_HOST, SMTP_PORT, SMTP_USER, "
            "SMTP_PASSWORD e SMTP_FROM no arquivo .env."
        )

    host = os.environ["SMTP_HOST"]
    porta = int(os.environ.get("SMTP_PORT", "587"))
    usuario = os.environ["SMTP_USER"]
    senha = os.environ["SMTP_PASSWORD"]
    remetente = os.environ.get("SMTP_FROM", usuario)

    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = assunto
    mensagem["From"] = remetente
    mensagem["To"] = ", ".join(destinatarios)
    mensagem.attach(MIMEText(corpo_html, "html", "utf-8"))

    with smtplib.SMTP(host, porta, timeout=15) as servidor:
        servidor.starttls()
        servidor.login(usuario, senha)
        servidor.sendmail(remetente, destinatarios, mensagem.as_string())
