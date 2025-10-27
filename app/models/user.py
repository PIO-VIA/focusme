"""
Modèle User - Gestion des utilisateurs de l'application Focus
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """Énumération des rôles utilisateur"""
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """
    Modèle utilisateur principal
    Gère l'authentification, les profils et les rôles
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Informations personnelles
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)

    # Statut du compte
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Tokens de vérification
    verification_token = Column(String(255), nullable=True)
    reset_password_token = Column(String(255), nullable=True)
    reset_password_expires = Column(DateTime, nullable=True)

    # Paramètres de l'utilisateur
    daily_limit_minutes = Column(Integer, default=120, nullable=False)  # Limite quotidienne en minutes
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    email_reminders = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relations
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    blocked_apps = relationship("BlockedApp", back_populates="user", cascade="all, delete-orphan")
    challenge_participations = relationship("ChallengeParticipant", back_populates="user", cascade="all, delete-orphan")
    created_challenges = relationship("Challenge", back_populates="creator", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"

    @property
    def is_admin(self) -> bool:
        """Vérifie si l'utilisateur est administrateur"""
        return self.role == UserRole.ADMIN
