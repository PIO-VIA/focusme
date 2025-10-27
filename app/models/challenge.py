"""
Modèle Challenge - Gestion des challenges entre utilisateurs
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum

from app.database import Base


class ChallengeStatus(str, enum.Enum):
    """Statut du challenge"""
    PENDING = "pending"  # En attente de participants
    ACTIVE = "active"  # En cours
    COMPLETED = "completed"  # Terminé
    CANCELLED = "cancelled"  # Annulé


class ChallengeType(str, enum.Enum):
    """Type de challenge"""
    MINIMIZE_TIME = "minimize_time"  # Minimiser le temps sur les réseaux sociaux
    DAILY_GOAL = "daily_goal"  # Atteindre un objectif quotidien
    WEEKLY_GOAL = "weekly_goal"  # Objectif hebdomadaire


class Challenge(Base):
    """
    Modèle principal des challenges
    Un challenge peut avoir plusieurs participants
    """
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Informations du challenge
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    challenge_type = Column(SQLEnum(ChallengeType), default=ChallengeType.MINIMIZE_TIME, nullable=False)
    status = Column(SQLEnum(ChallengeStatus), default=ChallengeStatus.PENDING, nullable=False, index=True)

    # Objectif du challenge (en minutes)
    target_minutes = Column(Integer, nullable=False)  # Objectif de temps (ex: ne pas dépasser 60 min/jour)

    # Dates
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    # Paramètres
    max_participants = Column(Integer, default=10, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)  # Challenge privé ou public
    invitation_code = Column(String(50), unique=True, nullable=True)  # Code pour rejoindre le challenge

    # Résultats (calculés à la fin)
    winner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    results_sent = Column(Boolean, default=False, nullable=False)  # Email de résultats envoyé

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_challenges")
    winner = relationship("User", foreign_keys=[winner_id])
    participants = relationship("ChallengeParticipant", back_populates="challenge", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Challenge {self.title} status={self.status}>"

    @property
    def is_active(self) -> bool:
        """Vérifie si le challenge est actuellement actif"""
        now = datetime.utcnow()
        return self.status == ChallengeStatus.ACTIVE and self.start_date <= now <= self.end_date

    @property
    def duration_days(self) -> int:
        """Calcule la durée du challenge en jours"""
        return (self.end_date - self.start_date).days


class ChallengeParticipant(Base):
    """
    Table intermédiaire pour les participants aux challenges
    Stocke les scores et statistiques de chaque participant
    """
    __tablename__ = "challenge_participants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Statistiques du participant
    total_time_minutes = Column(Float, default=0.0, nullable=False)  # Temps total sur les réseaux pendant le challenge
    daily_average = Column(Float, default=0.0, nullable=False)  # Moyenne quotidienne
    goal_achieved = Column(Boolean, default=False, nullable=False)  # Objectif atteint ou non

    # Score (calculé selon le type de challenge)
    score = Column(Float, default=0.0, nullable=False)
    rank = Column(Integer, nullable=True)  # Classement final

    # Statut
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    challenge = relationship("Challenge", back_populates="participants")
    user = relationship("User", back_populates="challenge_participations")

    def __repr__(self) -> str:
        return f"<ChallengeParticipant challenge_id={self.challenge_id} user_id={self.user_id} score={self.score}>"
