"""
Service d'envoi d'emails
Gère tous les envois d'emails de l'application
"""
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from typing import List, Dict, Any
from pydantic import EmailStr
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Configuration de FastMail
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_TLS,
    MAIL_SSL_TLS=settings.MAIL_SSL,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=True
)

fm = FastMail(conf)


async def send_email(
    subject: str,
    recipients: List[EmailStr],
    body: str,
    subtype: MessageType = MessageType.html
) -> bool:
    """
    Envoie un email

    Args:
        subject: Sujet de l'email
        recipients: Liste des destinataires
        body: Corps de l'email (HTML ou texte)
        subtype: Type du message (html ou plain)

    Returns:
        bool: True si l'email a été envoyé, False sinon
    """
    try:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=subtype
        )
        await fm.send_message(message)
        logger.info(f"Email envoyé à {recipients}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email à {recipients}: {e}")
        return False


async def send_verification_email(email: EmailStr, username: str, token: str) -> bool:
    """
    Envoie un email de vérification de compte

    Args:
        email: Email du destinataire
        username: Nom d'utilisateur
        token: Token de vérification

    Returns:
        bool: True si l'email a été envoyé
    """
    verification_url = f"{settings.EMAIL_VERIFY_URL}?token={token}"

    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Bienvenue sur Focus!</h1>
            </div>
            <div class="content">
                <p>Bonjour <strong>{username}</strong>,</p>
                <p>Merci de vous être inscrit sur Focus, l'application qui vous aide à reprendre le contrôle de votre temps.</p>
                <p>Pour activer votre compte, veuillez cliquer sur le bouton ci-dessous:</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">Vérifier mon email</a>
                </p>
                <p>Si le bouton ne fonctionne pas, copiez-collez ce lien dans votre navigateur:</p>
                <p><a href="{verification_url}">{verification_url}</a></p>
                <p>Ce lien expirera dans 24 heures.</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé automatiquement par Focus. Merci de ne pas y répondre.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(
        subject="Vérifiez votre compte Focus",
        recipients=[email],
        body=body
    )


async def send_password_reset_email(email: EmailStr, username: str, token: str) -> bool:
    """
    Envoie un email de réinitialisation de mot de passe

    Args:
        email: Email du destinataire
        username: Nom d'utilisateur
        token: Token de réinitialisation

    Returns:
        bool: True si l'email a été envoyé
    """
    reset_url = f"{settings.PASSWORD_RESET_URL}?token={token}"

    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #FF9800; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #FF9800;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Réinitialisation de mot de passe</h1>
            </div>
            <div class="content">
                <p>Bonjour <strong>{username}</strong>,</p>
                <p>Nous avons reçu une demande de réinitialisation de mot de passe pour votre compte Focus.</p>
                <p>Pour réinitialiser votre mot de passe, cliquez sur le bouton ci-dessous:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Réinitialiser mon mot de passe</a>
                </p>
                <p>Si le bouton ne fonctionne pas, copiez-collez ce lien dans votre navigateur:</p>
                <p><a href="{reset_url}">{reset_url}</a></p>
                <p>Ce lien expirera dans 1 heure.</p>
                <p><strong>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</strong></p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé automatiquement par Focus. Merci de ne pas y répondre.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(
        subject="Réinitialisation de votre mot de passe Focus",
        recipients=[email],
        body=body
    )


async def send_daily_reminder_email(
    email: EmailStr,
    username: str,
    total_minutes: float,
    top_apps: List[Dict[str, Any]]
) -> bool:
    """
    Envoie un rappel quotidien avec les statistiques

    Args:
        email: Email du destinataire
        username: Nom d'utilisateur
        total_minutes: Temps total passé aujourd'hui
        top_apps: Liste des apps les plus utilisées

    Returns:
        bool: True si l'email a été envoyé
    """
    hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)

    apps_html = ""
    for app in top_apps[:3]:
        app_minutes = app.get("minutes", 0)
        app_hours = int(app_minutes // 60)
        app_mins = int(app_minutes % 60)
        apps_html += f"<li><strong>{app.get('name')}</strong>: {app_hours}h {app_mins}min</li>"

    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .stats {{ background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Votre rapport quotidien Focus</h1>
            </div>
            <div class="content">
                <p>Bonjour <strong>{username}</strong>,</p>
                <p>Voici votre résumé d'aujourd'hui:</p>
                <div class="stats">
                    <h3>Temps total: {hours}h {minutes}min</h3>
                    <p><strong>Top 3 des applications:</strong></p>
                    <ul>{apps_html}</ul>
                </div>
                <p>Continuez à progresser vers vos objectifs!</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé automatiquement par Focus. Merci de ne pas y répondre.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(
        subject="Votre rapport Focus du jour",
        recipients=[email],
        body=body
    )


async def send_challenge_results_email(
    email: EmailStr,
    username: str,
    challenge_title: str,
    rank: int,
    total_participants: int,
    winner_name: str
) -> bool:
    """
    Envoie les résultats d'un challenge

    Args:
        email: Email du destinataire
        username: Nom d'utilisateur
        challenge_title: Titre du challenge
        rank: Classement du participant
        total_participants: Nombre total de participants
        winner_name: Nom du gagnant

    Returns:
        bool: True si l'email a été envoyé
    """
    is_winner = rank == 1
    color = "#4CAF50" if is_winner else "#2196F3"
    message = "Félicitations! Vous avez gagné ce challenge!" if is_winner else f"Vous avez terminé {rank}e sur {total_participants} participants."

    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .stats {{ background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Résultats du Challenge</h1>
                <h2>{challenge_title}</h2>
            </div>
            <div class="content">
                <p>Bonjour <strong>{username}</strong>,</p>
                <p>{message}</p>
                <div class="stats">
                    <p><strong>Gagnant:</strong> {winner_name}</p>
                    <p><strong>Votre classement:</strong> {rank}e / {total_participants}</p>
                </div>
                <p>Merci d'avoir participé! Continuez vos efforts pour le prochain challenge!</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé automatiquement par Focus. Merci de ne pas y répondre.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(
        subject=f"Résultats du challenge: {challenge_title}",
        recipients=[email],
        body=body
    )


async def send_limit_warning_email(
    email: EmailStr,
    username: str,
    app_name: str,
    usage_percentage: float
) -> bool:
    """
    Envoie un avertissement quand l'utilisateur approche de sa limite

    Args:
        email: Email du destinataire
        username: Nom d'utilisateur
        app_name: Nom de l'application
        usage_percentage: Pourcentage d'utilisation

    Returns:
        bool: True si l'email a été envoyé
    """
    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #FF5722; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .warning {{ background-color: #FFF3E0; padding: 15px; border-left: 4px solid #FF9800; margin: 15px 0; }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Attention: Limite bientôt atteinte!</h1>
            </div>
            <div class="content">
                <p>Bonjour <strong>{username}</strong>,</p>
                <div class="warning">
                    <p><strong>Vous avez utilisé {usage_percentage:.0f}% de votre limite quotidienne pour {app_name}.</strong></p>
                </div>
                <p>Il est temps de faire une pause et de vous concentrer sur d'autres activités!</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé automatiquement par Focus. Merci de ne pas y répondre.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return await send_email(
        subject=f"Avertissement: Limite de temps pour {app_name}",
        recipients=[email],
        body=body
    )
