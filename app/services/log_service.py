"""
Service de logging
Enregistre toutes les actions importantes dans la base de données
"""
from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional
import logging

from app.models import Log, User
from app.models.log import LogAction, LogLevel

logger = logging.getLogger(__name__)


async def create_log(
    db: Session,
    action: LogAction,
    message: str,
    user_id: Optional[int] = None,
    level: LogLevel = LogLevel.INFO,
    details: Optional[str] = None,
    request: Optional[Request] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None
) -> Log:
    """
    Crée un nouveau log dans la base de données

    Args:
        db: Session de base de données
        action: Action effectuée
        message: Message du log
        user_id: ID de l'utilisateur (optionnel)
        level: Niveau du log
        details: Détails additionnels
        request: Objet Request FastAPI (pour extraire IP et user agent)
        resource_type: Type de ressource affectée
        resource_id: ID de la ressource affectée

    Returns:
        Log: Log créé
    """
    try:
        # Extraction des informations de la requête
        ip_address = None
        user_agent = None
        endpoint = None

        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            endpoint = f"{request.method} {request.url.path}"

        # Création du log
        log = Log(
            user_id=user_id,
            action=action,
            level=level,
            message=message,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            resource_type=resource_type,
            resource_id=resource_id
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        logger.info(f"Log créé: {action} - {message}")
        return log

    except Exception as e:
        logger.error(f"Erreur lors de la création du log: {e}")
        db.rollback()
        raise


async def log_user_login(db: Session, user: User, request: Request) -> None:
    """Log une connexion utilisateur"""
    await create_log(
        db=db,
        action=LogAction.LOGIN,
        message=f"Connexion de l'utilisateur {user.username}",
        user_id=user.id,
        level=LogLevel.INFO,
        request=request,
        resource_type="user",
        resource_id=user.id
    )


async def log_user_register(db: Session, user: User, request: Request) -> None:
    """Log une inscription utilisateur"""
    await create_log(
        db=db,
        action=LogAction.REGISTER,
        message=f"Nouvel utilisateur enregistré: {user.username}",
        user_id=user.id,
        level=LogLevel.INFO,
        request=request,
        resource_type="user",
        resource_id=user.id
    )


async def log_email_verified(db: Session, user: User) -> None:
    """Log une vérification d'email"""
    await create_log(
        db=db,
        action=LogAction.EMAIL_VERIFIED,
        message=f"Email vérifié pour {user.username}",
        user_id=user.id,
        level=LogLevel.INFO,
        resource_type="user",
        resource_id=user.id
    )


async def log_password_reset_requested(db: Session, user: User, request: Request) -> None:
    """Log une demande de réinitialisation de mot de passe"""
    await create_log(
        db=db,
        action=LogAction.PASSWORD_RESET_REQUESTED,
        message=f"Demande de réinitialisation de mot de passe pour {user.username}",
        user_id=user.id,
        level=LogLevel.WARNING,
        request=request,
        resource_type="user",
        resource_id=user.id
    )


async def log_password_reset_completed(db: Session, user: User) -> None:
    """Log une réinitialisation de mot de passe réussie"""
    await create_log(
        db=db,
        action=LogAction.PASSWORD_RESET_COMPLETED,
        message=f"Mot de passe réinitialisé pour {user.username}",
        user_id=user.id,
        level=LogLevel.INFO,
        resource_type="user",
        resource_id=user.id
    )


async def log_app_blocked(
    db: Session,
    user_id: int,
    app_name: str,
    blocked_app_id: int
) -> None:
    """Log un blocage d'application"""
    await create_log(
        db=db,
        action=LogAction.APP_BLOCKED,
        message=f"Application {app_name} bloquée",
        user_id=user_id,
        level=LogLevel.INFO,
        resource_type="blocked_app",
        resource_id=blocked_app_id
    )


async def log_limit_reached(
    db: Session,
    user_id: int,
    app_name: str,
    minutes_used: float
) -> None:
    """Log qu'une limite a été atteinte"""
    await create_log(
        db=db,
        action=LogAction.LIMIT_REACHED,
        message=f"Limite atteinte pour {app_name} ({minutes_used} minutes)",
        user_id=user_id,
        level=LogLevel.WARNING,
        details=f"Application: {app_name}, Minutes utilisées: {minutes_used}"
    )


async def log_challenge_created(
    db: Session,
    user_id: int,
    challenge_id: int,
    challenge_title: str
) -> None:
    """Log la création d'un challenge"""
    await create_log(
        db=db,
        action=LogAction.CHALLENGE_CREATED,
        message=f"Challenge créé: {challenge_title}",
        user_id=user_id,
        level=LogLevel.INFO,
        resource_type="challenge",
        resource_id=challenge_id
    )


async def log_challenge_joined(
    db: Session,
    user_id: int,
    challenge_id: int,
    challenge_title: str
) -> None:
    """Log qu'un utilisateur a rejoint un challenge"""
    await create_log(
        db=db,
        action=LogAction.CHALLENGE_JOINED,
        message=f"Utilisateur a rejoint le challenge: {challenge_title}",
        user_id=user_id,
        level=LogLevel.INFO,
        resource_type="challenge",
        resource_id=challenge_id
    )


async def log_challenge_completed(
    db: Session,
    challenge_id: int,
    challenge_title: str,
    winner_id: Optional[int] = None
) -> None:
    """Log la fin d'un challenge"""
    await create_log(
        db=db,
        action=LogAction.CHALLENGE_COMPLETED,
        message=f"Challenge terminé: {challenge_title}",
        user_id=winner_id,
        level=LogLevel.INFO,
        resource_type="challenge",
        resource_id=challenge_id
    )


async def log_user_deleted(
    db: Session,
    admin_id: int,
    deleted_user_id: int,
    deleted_username: str
) -> None:
    """Log la suppression d'un utilisateur par un admin"""
    await create_log(
        db=db,
        action=LogAction.USER_DELETED,
        message=f"Utilisateur supprimé: {deleted_username}",
        user_id=admin_id,
        level=LogLevel.WARNING,
        resource_type="user",
        resource_id=deleted_user_id
    )


async def log_admin_access(
    db: Session,
    admin_id: int,
    request: Request,
    details: Optional[str] = None
) -> None:
    """Log un accès à une fonction admin"""
    await create_log(
        db=db,
        action=LogAction.ADMIN_ACCESS,
        message="Accès aux fonctions d'administration",
        user_id=admin_id,
        level=LogLevel.INFO,
        request=request,
        details=details
    )


async def log_email_sent(
    db: Session,
    user_id: Optional[int],
    email_type: str,
    success: bool
) -> None:
    """Log l'envoi d'un email"""
    action = LogAction.EMAIL_SENT if success else LogAction.EMAIL_FAILED
    level = LogLevel.INFO if success else LogLevel.ERROR
    message = f"Email {email_type} {'envoyé' if success else 'échoué'}"

    await create_log(
        db=db,
        action=action,
        message=message,
        user_id=user_id,
        level=level,
        details=f"Type: {email_type}"
    )
