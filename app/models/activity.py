"""
Modèle Activity - Suivi du temps d'utilisation des applications
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date

from app.database import Base


class Activity(Base):
    """
    Modèle pour suivre l'utilisation des applications par les utilisateurs
    Enregistre le temps passé sur chaque application
    """
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Informations sur l'application
    app_name = Column(String(100), nullable=False, index=True)  # ex: "Instagram", "TikTok", "Facebook"
    app_package = Column(String(255), nullable=True)  # ex: "com.instagram.android"
    app_category = Column(String(50), default="social_media", nullable=False)  # social_media, game, productivity, etc.

    # Temps d'utilisation
    duration_minutes = Column(Float, default=0.0, nullable=False)  # Durée en minutes
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Date de l'activité (pour les statistiques quotidiennes)
    activity_date = Column(Date, default=date.today, nullable=False, index=True)

    # Métadonnées
    device_type = Column(String(50), nullable=True)  # "android", "ios", "web"
    session_id = Column(String(100), nullable=True)  # Pour regrouper les sessions

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    user = relationship("User", back_populates="activities")

    def __repr__(self) -> str:
        return f"<Activity user_id={self.user_id} app={self.app_name} duration={self.duration_minutes}min>"

    @property
    def duration_hours(self) -> float:
        """Retourne la durée en heures"""
        return round(self.duration_minutes / 60, 2)
