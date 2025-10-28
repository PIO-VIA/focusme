"""
Schémas Pydantic pour les utilisateurs
Validation des données d'entrée et de sortie
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


# Schémas de base
class UserBase(BaseModel):
    """Schéma de base pour un utilisateur"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur"""
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        """Valide la complexité du mot de passe"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        if not any(char.isupper() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        if not any(char.islower() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une minuscule')
        return v


class UserLogin(BaseModel):
    """Schéma pour la connexion"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour d'un utilisateur"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    daily_limit_minutes: Optional[int] = Field(None, ge=0, le=1440)
    notifications_enabled: Optional[bool] = None
    email_reminders: Optional[bool] = None


class UserResponse(UserBase):
    """Schéma de réponse pour un utilisateur"""
    id: int
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    role: UserRole
    daily_limit_minutes: int
    notifications_enabled: bool
    email_reminders: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """Schéma public d'un utilisateur (pour les listes, challenges, etc.)"""
    id: int
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


# Schémas d'authentification
class Token(BaseModel):
    """Schéma pour le token JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Payload du token JWT"""
    sub: int  # user_id
    exp: datetime


class EmailVerification(BaseModel):
    """Schéma pour la vérification d'email"""
    token: str


class PasswordResetRequest(BaseModel):
    """Schéma pour demander une réinitialisation de mot de passe"""
    email: EmailStr


class PasswordReset(BaseModel):
    """Schéma pour réinitialiser le mot de passe"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
    def validate_password(cls, v):
        """Valide la complexité du mot de passe"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        if not any(char.isupper() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        if not any(char.islower() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une minuscule')
        return v


class PasswordChange(BaseModel):
    """Schéma pour changer le mot de passe"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
    def validate_password(cls, v):
        """Valide la complexité du mot de passe"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        if not any(char.isupper() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        if not any(char.islower() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une minuscule')
        return v


# Schémas pour l'administration
class UserAdmin(UserResponse):
    """Schéma admin avec toutes les informations"""
    verification_token: Optional[str]
    reset_password_token: Optional[str]

    class Config:
        from_attributes = True
