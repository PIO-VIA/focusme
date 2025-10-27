"""
Modèle Log - Système de logs et audit pour l'administration
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.database import Base


class LogLevel(str, enum.Enum):
    """Niveau de gravité du log"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogAction(str, enum.Enum):
    """Types d'actions loggées"""
    # Authentification
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    EMAIL_VERIFIED = "email_verified"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"

    # Activités
    ACTIVITY_CREATED = "activity_created"
    ACTIVITY_UPDATED = "activity_updated"
    ACTIVITY_DELETED = "activity_deleted"

    # Blocages
    APP_BLOCKED = "app_blocked"
    APP_UNBLOCKED = "app_unblocked"
    LIMIT_REACHED = "limit_reached"
    BLOCKED_APP_CREATED = "blocked_app_created"
    BLOCKED_APP_DELETED = "blocked_app_deleted"

    # Challenges
    CHALLENGE_CREATED = "challenge_created"
    CHALLENGE_JOINED = "challenge_joined"
    CHALLENGE_LEFT = "challenge_left"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_CANCELLED = "challenge_cancelled"

    # Administration
    USER_DELETED = "user_deleted"
    USER_SUSPENDED = "user_suspended"
    USER_ACTIVATED = "user_activated"
    ADMIN_ACCESS = "admin_access"

    # Emails
    EMAIL_SENT = "email_sent"
    EMAIL_FAILED = "email_failed"


class Log(Base):
    """
    Modèle de log pour l'audit et le monitoring
    Enregistre toutes les actions importantes du système
    """
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Informations du log
    action = Column(SQLEnum(LogAction), nullable=False, index=True)
    level = Column(SQLEnum(LogLevel), default=LogLevel.INFO, nullable=False, index=True)
    message = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)  # Détails additionnels en JSON

    # Contexte
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(String(255), nullable=True)
    endpoint = Column(String(100), nullable=True)  # Endpoint API appelé

    # Métadonnées
    resource_type = Column(String(50), nullable=True)  # Type de ressource (user, challenge, etc.)
    resource_id = Column(Integer, nullable=True)  # ID de la ressource

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relations
    user = relationship("User", back_populates="logs")

    def __repr__(self) -> str:
        return f"<Log {self.action} level={self.level} user_id={self.user_id}>"
