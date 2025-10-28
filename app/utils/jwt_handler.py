"""
Gestionnaire JWT
Création et vérification des tokens JWT pour l'authentification
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

# Security scheme pour FastAPI
security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un token d'accès JWT

    Args:
        data: Données à encoder dans le token
        expires_delta: Durée de validité du token

    Returns:
        str: Token JWT encodé
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Crée un refresh token JWT

    Args:
        data: Données à encoder dans le token

    Returns:
        str: Refresh token JWT encodé
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Décode et vérifie un token JWT

    Args:
        token: Token JWT à décoder

    Returns:
        Dict: Payload du token

    Raises:
        HTTPException: Si le token est invalide ou expiré
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Récupère l'utilisateur actuel depuis le token JWT

    Args:
        credentials: Credentials HTTP Bearer
        db: Session de base de données

    Returns:
        User: Utilisateur authentifié

    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    token = credentials.credentials
    payload = decode_token(token)

    # Vérifie que c'est un access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Type de token invalide",
        )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )

    # Récupère l'utilisateur depuis la base de données
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur désactivé",
        )

    return user


def get_current_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Récupère l'utilisateur actuel et vérifie qu'il est vérifié

    Args:
        current_user: Utilisateur actuel

    Returns:
        User: Utilisateur vérifié

    Raises:
        HTTPException: Si l'utilisateur n'est pas vérifié
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email non vérifié. Veuillez vérifier votre email.",
        )
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Récupère l'utilisateur actuel et vérifie qu'il est administrateur

    Args:
        current_user: Utilisateur actuel

    Returns:
        User: Utilisateur administrateur

    Raises:
        HTTPException: Si l'utilisateur n'est pas administrateur
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis",
        )
    return current_user


def create_tokens_for_user(user_id: int) -> Dict[str, str]:
    """
    Crée les tokens d'accès et de rafraîchissement pour un utilisateur

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Dict: Dictionnaire contenant access_token et refresh_token
    """
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def refresh_access_token(refresh_token: str) -> str:
    """
    Crée un nouveau access token à partir d'un refresh token

    Args:
        refresh_token: Refresh token valide

    Returns:
        str: Nouveau access token

    Raises:
        HTTPException: Si le refresh token est invalide
    """
    payload = decode_token(refresh_token)

    # Vérifie que c'est un refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Type de token invalide",
        )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )

    # Crée un nouveau access token
    return create_access_token(data={"sub": user_id})
