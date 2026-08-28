import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def smtp_configurado() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def enviar_email(
    destinatarios: list[str],
    assunto: str,
    corpo_html: str,
    anexos: list[tuple[str, str]] | None = None,
) -> None:
    """
    Envia um e-mail via SMTP, usando as credenciais configuradas no .env.
    Lanca excecao se o SMTP nao estiver configurado ou o envio falhar -
    quem chama decide como tratar isso (logar, devolver erro na API, etc).

    anexos: lista de tuplas (caminho_no_disco, nome_original_do_arquivo).
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

    mensagem = MIMEMultipart("mixed")
    mensagem["Subject"] = assunto
    mensagem["From"] = remetente
    mensagem["To"] = ", ".join(destinatarios)
    mensagem.attach(MIMEText(corpo_html, "html", "utf-8"))

    for caminho, nome_original in anexos or []:
        if not os.path.exists(caminho):
            continue
        with open(caminho, "rb") as f:
            conteudo = f.read()

        extensao = os.path.splitext(nome_original)[1].lower()
        if extensao in (".jpg", ".jpeg", ".png"):
            subtipo = "jpeg" if extensao in (".jpg", ".jpeg") else "png"
            parte = MIMEImage(conteudo, _subtype=subtipo)
        else:
            parte = MIMEApplication(conteudo)
        parte.add_header("Content-Disposition", "attachment", filename=nome_original)
        mensagem.attach(parte)

    with smtplib.SMTP(host, porta, timeout=20) as servidor:
        servidor.starttls()
        servidor.login(usuario, senha)
        servidor.sendmail(remetente, destinatarios, mensagem.as_string())
