"""
Serviço de envio de emails.
"""

from typing import List
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

from app.core.config import settings


def get_email_config() -> ConnectionConfig:
    """Retorna a configuração do FastMail baseada nas settings."""
    return ConnectionConfig(
        MAIL_USERNAME=settings.smtp_user,
        MAIL_PASSWORD=settings.smtp_password,
        MAIL_FROM=settings.smtp_from_email,
        MAIL_PORT=settings.smtp_port,
        MAIL_SERVER=settings.smtp_host,
        MAIL_FROM_NAME=settings.smtp_from_name,
        MAIL_STARTTLS=settings.smtp_use_tls,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=bool(settings.smtp_user and settings.smtp_password),
        VALIDATE_CERTS=True,
    )


async def send_email(
    to: List[EmailStr] | EmailStr,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> None:
    """
    Envia um email.

    Args:
        to: Email(s) do(s) destinatário(s)
        subject: Assunto do email
        html_body: Corpo HTML do email
        text_body: Corpo em texto plano (opcional, será gerado automaticamente se não fornecido)
    """
    # Verifica se SMTP está configurado
    if not settings.smtp_host:
        print("⚠️  SMTP não configurado. Email NÃO foi enviado.")
        print(f"   Para: {to}")
        print(f"   Assunto: {subject}")
        return

    # Garante que 'to' seja uma lista
    recipients = [to] if isinstance(to, str) else to

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=html_body,
        subtype=MessageType.html,
    )

    config = get_email_config()
    fm = FastMail(config)

    try:
        await fm.send_message(message)
        print(f"✅ Email enviado para: {', '.join(recipients)}")
    except Exception as e:
        print(f"❌ Erro ao enviar email para {', '.join(recipients)}: {e}")
        raise


async def send_project_invite_email(
    to_email: str,
    inviter_name: str,
    project_name: str,
    role: str,
) -> None:
    """
    Envia email de convite para um projeto.

    Args:
        to_email: Email do convidado
        inviter_name: Nome de quem enviou o convite
        project_name: Nome do projeto
        role: Permissão concedida (viewer, member, admin)
    """
    role_names = {
        "viewer": "Visualizador",
        "member": "Membro",
        "admin": "Administrador",
    }
    role_display = role_names.get(role, role)

    subject = f"Convite para o projeto {project_name}"

    html_body = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Convite para Projeto</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: #2563eb;
        }}
        h1 {{
            color: #1a1a1a;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .project-info {{
            background-color: #f8fafc;
            border-left: 4px solid #2563eb;
            padding: 16px;
            margin: 24px 0;
            border-radius: 4px;
        }}
        .project-info strong {{
            color: #2563eb;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #2563eb;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            margin: 20px 0;
            font-weight: 500;
        }}
        .cta-button:hover {{
            background-color: #1d4ed8;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            font-size: 14px;
            color: #6b7280;
        }}
        .note {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px;
            margin: 20px 0;
            border-radius: 4px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Tactyo</div>
        </div>

        <h1>Você foi convidado para um projeto!</h1>

        <p>Olá,</p>

        <p><strong>{inviter_name}</strong> convidou você para colaborar no projeto:</p>

        <div class="project-info">
            <strong>{project_name}</strong><br>
            Permissão: {role_display}
        </div>

        <p>Para aceitar o convite, acesse a plataforma Tactyo e visualize seus convites pendentes:</p>

        <div style="text-align: center;">
            <a href="{settings.frontend_url}/invites" class="cta-button">
                Ver Convites
            </a>
        </div>

        <div class="note">
            <strong>ℹ️ Nota:</strong> Se você ainda não tem uma conta no Tactyo, será necessário criar uma usando este email ({to_email}) para poder aceitar o convite.
        </div>

        <div class="footer">
            <p>Este é um email automático da plataforma Tactyo.<br>
            Gestão integrada ao GitHub Projects.</p>
        </div>
    </div>
</body>
</html>
"""

    await send_email(
        to=to_email,
        subject=subject,
        html_body=html_body,
    )


async def send_email_verification(
    to_email: str,
    verification_token: str,
    user_name: str | None = None,
) -> None:
    """
    Envia email de verificação de conta.

    Args:
        to_email: Email do usuário
        verification_token: Token de verificação gerado
        user_name: Nome do usuário (opcional)
    """
    verification_url = f"{settings.frontend_url}/verify-email?token={verification_token}"
    display_name = user_name or to_email

    subject = "Confirme seu email - Tactyo"

    html_body = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confirme seu Email</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: #2563eb;
        }}
        h1 {{
            color: #1a1a1a;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #2563eb;
            color: white !important;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            margin: 20px 0;
            font-weight: 500;
        }}
        .cta-button:hover {{
            background-color: #1d4ed8;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            font-size: 14px;
            color: #6b7280;
        }}
        .note {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px;
            margin: 20px 0;
            border-radius: 4px;
            font-size: 14px;
        }}
        .token-box {{
            background-color: #f8fafc;
            border: 1px solid #e5e7eb;
            padding: 12px;
            margin: 20px 0;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Tactyo</div>
        </div>

        <h1>Confirme seu endereço de email</h1>

        <p>Olá{', ' + display_name if user_name else ''},</p>

        <p>Obrigado por criar sua conta no Tactyo! Para começar a usar a plataforma, precisamos confirmar seu endereço de email.</p>

        <p>Clique no botão abaixo para verificar sua conta:</p>

        <div style="text-align: center;">
            <a href="{verification_url}" class="cta-button">
                Confirmar Email
            </a>
        </div>

        <div class="note">
            <strong>⏱️ Importante:</strong> Este link expira em 24 horas. Se você não solicitou esta conta, pode ignorar este email com segurança.
        </div>

        <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
            Se o botão não funcionar, copie e cole este link no seu navegador:
        </p>
        <div class="token-box">
            {verification_url}
        </div>

        <div class="footer">
            <p>Este é um email automático da plataforma Tactyo.<br>
            Gestão integrada ao GitHub Projects.</p>
        </div>
    </div>
</body>
</html>
"""

    await send_email(
        to=to_email,
        subject=subject,
        html_body=html_body,
    )
