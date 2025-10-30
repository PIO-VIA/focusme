"""
Router d'authentification
Gère l'inscription, la connexion, la vérification d'email et la réinitialisation du mot de passe
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User
from app.schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    EmailVerification,
    PasswordResetRequest,
    PasswordReset
)
from app.utils.security import (
    get_password_hash,
    verify_password,
    generate_verification_token,
    generate_reset_token,
    is_token_expired,
    create_expiration_date
)
from app.utils.jwt_handler import create_tokens_for_user, refresh_access_token
from app.services.email_service import send_verification_email, send_password_reset_email
from app.services.log_service import log_user_login, log_user_register, log_email_verified, log_password_reset_requested, log_password_reset_completed, log_email_sent

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """
    Inscription d'un nouvel utilisateur

    - Crée un nouveau compte utilisateur
    - Envoie un email de vérification
    - Retourne les informations de l'utilisateur
    """
    # Vérifie si l'email existe déjà
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )

    # Vérifie si le username existe déjà
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà pris"
        )

    # Crée le nouvel utilisateur
    verification_token = generate_verification_token()

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        verification_token=verification_token,
        is_verified=False,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Envoie l'email de vérification
    email_sent = await send_verification_email(
        email=new_user.email,
        username=new_user.username,
        token=verification_token
    )

    # Log l'inscription
    await log_user_register(db, new_user, request)
    await log_email_sent(db, new_user.id, "verification", email_sent)

    return new_user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Connexion d'un utilisateur

    - Vérifie les identifiants
    - Retourne les tokens JWT (access + refresh)
    """
    # Recherche l'utilisateur par email
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé"
        )

    # Met à jour la date de dernière connexion
    user.last_login = datetime.utcnow()
    db.commit()

    # Log la connexion
    await log_user_login(db, user, request)

    # Crée et retourne les tokens
    tokens = create_tokens_for_user(user.id)
    return tokens


@router.post("/verify-email")
async def verify_email(verification: EmailVerification, db: Session = Depends(get_db)):
    """
    Vérifie l'email d'un utilisateur

    - Valide le token de vérification
    - Active le compte
    """
    user = db.query(User).filter(User.verification_token == verification.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de vérification invalide"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email déjà vérifié"
        )

    # Vérifie le compte
    user.is_verified = True
    user.verification_token = None
    db.commit()

    # Log la vérification
    await log_email_verified(db, user)

    return {"message": "Email vérifié avec succès"}


@router.post("/resend-verification")
async def resend_verification_email(email: str, db: Session = Depends(get_db)):
    """
    Renvoie l'email de vérification
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Ne révèle pas si l'email existe ou non (sécurité)
        return {"message": "Si l'email existe, un nouveau lien de vérification a été envoyé"}

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email déjà vérifié"
        )

    # Génère un nouveau token
    verification_token = generate_verification_token()
    user.verification_token = verification_token
    db.commit()

    # Envoie l'email
    email_sent = await send_verification_email(
        email=user.email,
        username=user.username,
        token=verification_token
    )

    await log_email_sent(db, user.id, "verification_resend", email_sent)

    return {"message": "Email de vérification envoyé"}


@router.post("/forgot-password")
async def forgot_password(request_data: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    """
    Demande de réinitialisation du mot de passe

    - Envoie un email avec un lien de réinitialisation
    """
    user = db.query(User).filter(User.email == request_data.email).first()

    if not user:
        # Ne révèle pas si l'email existe ou non (sécurité)
        return {"message": "Si l'email existe, un lien de réinitialisation a été envoyé"}

    # Génère un token de réinitialisation
    reset_token = generate_reset_token()
    user.reset_password_token = reset_token
    user.reset_password_expires = create_expiration_date(hours=1)  # Expire dans 1 heure
    db.commit()

    # Envoie l'email
    email_sent = await send_password_reset_email(
        email=user.email,
        username=user.username,
        token=reset_token
    )

    # Log la demande
    await log_password_reset_requested(db, user, request)
    await log_email_sent(db, user.id, "password_reset", email_sent)

    return {"message": "Email de réinitialisation envoyé"}


@router.post("/reset-password")
async def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """
    Réinitialise le mot de passe

    - Valide le token
    - Met à jour le mot de passe
    """
    user = db.query(User).filter(User.reset_password_token == reset_data.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de réinitialisation invalide"
        )

    # Vérifie l'expiration du token
    if is_token_expired(user.reset_password_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token expiré. Veuillez faire une nouvelle demande"
        )

    # Met à jour le mot de passe
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.reset_password_token = None
    user.reset_password_expires = None
    db.commit()

    # Log la réinitialisation
    await log_password_reset_completed(db, user)

    return {"message": "Mot de passe réinitialisé avec succès"}


@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_token: str):
    """
    Rafraîchit le token d'accès

    - Utilise le refresh token pour obtenir un nouveau access token
    """
    try:
        new_access_token = refresh_access_token(refresh_token)
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide"
        )


# ========================
# OAUTH GOOGLE
# ========================

@router.get("/google")
async def google_login():
    """
    Initie la connexion via Google OAuth

    Redirige l'utilisateur vers la page d'autorisation Google
    """
    from app.services.oauth_service import oauth_service
    from app.config import settings

    if not settings.OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth n'est pas configure"
        )

    try:
        authorization_url, state = await oauth_service.get_authorization_url(
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        return {
            "authorization_url": authorization_url,
            "state": state
        }

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'initialisation OAuth"
        )


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Callback OAuth Google

    Recoit le code d'autorisation et cree/connecte l'utilisateur

    Args:
        code: Code d'autorisation Google
        state: State pour verification CSRF
        db: Session de base de donnees
    """
    from app.services.oauth_service import oauth_service
    from app.config import settings

    if not settings.OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth n'est pas configure"
        )

    try:
        # Authentifie l'utilisateur via Google
        auth_data = await oauth_service.authenticate_with_google(
            db=db,
            code=code,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        user = auth_data['user']
        tokens = auth_data['tokens']

        # Log la connexion OAuth
        # await log_user_login(db, user, request)

        return {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "token_type": tokens['token_type'],
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url
            }
        }

    except Exception as e:
        logger.error(f"Erreur lors du callback OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Echec de l'authentification OAuth"
        )
