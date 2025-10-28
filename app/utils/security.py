"""
Utilitaires de sécurité
Gestion du hachage des mots de passe et des tokens de vérification
"""
from passlib.context import CryptContext
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

# Context pour le hachage des mots de passe avec bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie qu'un mot de passe en clair correspond au hash

    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash du mot de passe

    Returns:
        bool: True si le mot de passe est correct, False sinon
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt

    Args:
        password: Mot de passe en clair

    Returns:
        str: Hash du mot de passe
    """
    return pwd_context.hash(password)


def generate_token(length: int = 32) -> str:
    """
    Génère un token aléatoire sécurisé

    Args:
        length: Longueur du token (défaut: 32)

    Returns:
        str: Token aléatoire en hexadécimal
    """
    return secrets.token_urlsafe(length)


def generate_verification_token() -> str:
    """
    Génère un token de vérification d'email

    Returns:
        str: Token de vérification
    """
    return generate_token(32)


def generate_reset_token() -> str:
    """
    Génère un token de réinitialisation de mot de passe

    Returns:
        str: Token de réinitialisation
    """
    return generate_token(32)


def generate_invitation_code(length: int = 8) -> str:
    """
    Génère un code d'invitation pour les challenges

    Args:
        length: Longueur du code (défaut: 8)

    Returns:
        str: Code d'invitation alphanumérique
    """
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def is_token_expired(expiration_date: Optional[datetime]) -> bool:
    """
    Vérifie si un token est expiré

    Args:
        expiration_date: Date d'expiration du token

    Returns:
        bool: True si le token est expiré, False sinon
    """
    if not expiration_date:
        return True
    return datetime.utcnow() > expiration_date


def create_expiration_date(hours: int = 24) -> datetime:
    """
    Crée une date d'expiration

    Args:
        hours: Nombre d'heures avant expiration (défaut: 24)

    Returns:
        datetime: Date d'expiration
    """
    return datetime.utcnow() + timedelta(hours=hours)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Valide la force d'un mot de passe

    Args:
        password: Mot de passe à valider

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"

    if not any(char.isupper() for char in password):
        return False, "Le mot de passe doit contenir au moins une majuscule"

    if not any(char.islower() for char in password):
        return False, "Le mot de passe doit contenir au moins une minuscule"

    if not any(char.isdigit() for char in password):
        return False, "Le mot de passe doit contenir au moins un chiffre"

    # Optionnel: vérifier les caractères spéciaux
    # special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    # if not any(char in special_chars for char in password):
    #     return False, "Le mot de passe doit contenir au moins un caractère spécial"

    return True, None
