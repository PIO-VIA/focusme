"""
Modèle BlockedApp - Gestion des applications bloquées par utilisateur
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, time

from app.database import Base


class BlockedApp(Base):
    """
    Modèle pour gérer les applications bloquées
    Permet de définir des règles de blocage par application
    """
    __tablename__ = "blocked_apps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Informations de l'application
    app_name = Column(String(100), nullable=False, index=True)
    app_package = Column(String(255), nullable=True)  # Package Android/iOS
    app_category = Column(String(50), default="social_media", nullable=False)

    # Configuration du blocage
    is_blocked = Column(Boolean, default=False, nullable=False)  # Statut actuel du blocage
    daily_limit_minutes = Column(Integer, default=60, nullable=False)  # Limite quotidienne
    current_usage_today = Column(Integer, default=0, nullable=False)  # Usage actuel aujourd'hui

    # Planification du blocage (optionnel)
    block_start_time = Column(Time, nullable=True)  # Heure de début de blocage (ex: 22:00)
    block_end_time = Column(Time, nullable=True)  # Heure de fin de blocage (ex: 08:00)
    block_on_weekends = Column(Boolean, default=False, nullable=False)

    # Notifications
    notify_at_percentage = Column(Integer, default=80, nullable=False)  # Notifier à X% de la limite
    notification_sent = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_blocked_at = Column(DateTime(timezone=True), nullable=True)
    last_reset_at = Column(DateTime(timezone=True), nullable=True)  # Dernière réinitialisation (minuit)

    # Relations
    user = relationship("User", back_populates="blocked_apps")

    def __repr__(self) -> str:
        status = "blocked" if self.is_blocked else "active"
        return f"<BlockedApp {self.app_name} user_id={self.user_id} status={status}>"

    @property
    def usage_percentage(self) -> float:
        """Calcule le pourcentage d'utilisation par rapport à la limite"""
        if self.daily_limit_minutes == 0:
            return 100.0
        return round((self.current_usage_today / self.daily_limit_minutes) * 100, 2)

    @property
    def should_be_blocked(self) -> bool:
        """Détermine si l'application devrait être bloquée"""
        return self.current_usage_today >= self.daily_limit_minutes

    @property
    def remaining_minutes(self) -> int:
        """Minutes restantes avant le blocage"""
        remaining = self.daily_limit_minutes - self.current_usage_today
        return max(0, remaining)
