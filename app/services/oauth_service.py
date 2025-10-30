"""
Service OAuth Google
Gere l'authentification via Google OAuth 2.0
"""
import logging
from typing import Optional, Dict, Any
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import OAuthError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserRole
from app.utils.security import generate_token
from app.utils.jwt_handler import create_tokens_for_user

logger = logging.getLogger(__name__)

# Configuration OAuth
oauth = OAuth()

if settings.OAUTH_ENABLED and settings.GOOGLE_CLIENT_ID:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    logger.info("OAuth Google configure avec succes")
else:
    logger.warning("OAuth Google non configure - verifiez les variables d'environnement")


class OAuthService:
    """Service pour gerer l'authentification OAuth"""

    @staticmethod
    async def get_authorization_url(redirect_uri: str) -> tuple[str, str]:
        """
        Genere l'URL d'autorisation Google

        Args:
            redirect_uri: URI de redirection apres auth

        Returns:
            tuple: (authorization_url, state)
        """
        if not settings.OAUTH_ENABLED:
            raise ValueError("OAuth n'est pas active")

        try:
            # Genere un state pour la securite CSRF
            state = generate_token(32)

            # Construit l'URL d'autorisation
            authorization_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={settings.GOOGLE_CLIENT_ID}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope=openid email profile&"
                f"state={state}"
            )

            logger.info(f"URL d'autorisation generee avec state: {state[:10]}...")
            return authorization_url, state

        except Exception as e:
            logger.error(f"Erreur lors de la generation de l'URL OAuth: {e}")
            raise

    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Echange le code d'autorisation contre un token d'acces

        Args:
            code: Code d'autorisation recu de Google
            redirect_uri: URI de redirection utilisee

        Returns:
            Dict: Token d'acces et informations utilisateur
        """
        import httpx

        if not settings.OAUTH_ENABLED:
            raise ValueError("OAuth n'est pas active")

        try:
            # Echange le code contre un token
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    'https://oauth2.googleapis.com/token',
                    data={
                        'code': code,
                        'client_id': settings.GOOGLE_CLIENT_ID,
                        'client_secret': settings.GOOGLE_CLIENT_SECRET,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code'
                    }
                )

                if token_response.status_code != 200:
                    logger.error(f"Erreur token exchange: {token_response.text}")
                    raise OAuthError(f"Echec de l'echange de code: {token_response.status_code}")

                token_data = token_response.json()

            # Recupere les informations utilisateur
            user_info = await OAuthService.get_user_info(token_data['access_token'])

            logger.info(f"Token echange avec succes pour {user_info.get('email')}")
            return {
                'access_token': token_data['access_token'],
                'user_info': user_info
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'echange de code OAuth: {e}")
            raise

    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """
        Recupere les informations de l'utilisateur depuis Google

        Args:
            access_token: Token d'acces Google

        Returns:
            Dict: Informations utilisateur
        """
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                user_response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )

                if user_response.status_code != 200:
                    raise OAuthError("Impossible de recuperer les infos utilisateur")

                return user_response.json()

        except Exception as e:
            logger.error(f"Erreur lors de la recuperation des infos utilisateur: {e}")
            raise

    @staticmethod
    def get_or_create_user(
        db: Session,
        google_id: str,
        email: str,
        name: str,
        picture: Optional[str] = None
    ) -> User:
        """
        Recupere ou cree un utilisateur a partir des infos Google

        Args:
            db: Session de base de donnees
            google_id: ID Google unique
            email: Email de l'utilisateur
            name: Nom complet
            picture: URL de la photo de profil

        Returns:
            User: Utilisateur cree ou existant
        """
        try:
            # Cherche l'utilisateur par email
            user = db.query(User).filter(User.email == email).first()

            if user:
                # Utilisateur existe - met a jour les infos si necessaire
                if not user.is_verified:
                    user.is_verified = True  # OAuth = email verifie
                if picture and not user.avatar_url:
                    user.avatar_url = picture
                db.commit()
                db.refresh(user)
                logger.info(f"Utilisateur existant connecte via OAuth: {email}")

            else:
                # Cree un nouvel utilisateur
                # Genere un username unique depuis l'email
                username = email.split('@')[0]
                counter = 1
                original_username = username
                while db.query(User).filter(User.username == username).first():
                    username = f"{original_username}{counter}"
                    counter += 1

                user = User(
                    username=username,
                    email=email,
                    full_name=name,
                    avatar_url=picture,
                    hashed_password=generate_token(32),  # Mot de passe aleatoire
                    is_verified=True,  # OAuth = email verifie
                    is_active=True,
                    role=UserRole.USER
                )

                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Nouvel utilisateur cree via OAuth: {email}")

            return user

        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la creation/recuperation utilisateur OAuth: {e}")
            raise

    @staticmethod
    async def authenticate_with_google(
        db: Session,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Authentifie un utilisateur via Google OAuth

        Args:
            db: Session de base de donnees
            code: Code d'autorisation
            redirect_uri: URI de redirection

        Returns:
            Dict: Tokens JWT et infos utilisateur
        """
        try:
            # Echange le code contre les infos utilisateur
            oauth_data = await OAuthService.exchange_code_for_token(code, redirect_uri)
            user_info = oauth_data['user_info']

            # Cree ou recupere l'utilisateur
            user = OAuthService.get_or_create_user(
                db=db,
                google_id=user_info['id'],
                email=user_info['email'],
                name=user_info.get('name', user_info['email']),
                picture=user_info.get('picture')
            )

            # Genere les tokens JWT
            tokens = create_tokens_for_user(user.id)

            logger.info(f"Authentification OAuth reussie pour {user.email}")

            return {
                'user': user,
                'tokens': tokens
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'authentification OAuth: {e}")
            raise


# Instance globale du service
oauth_service = OAuthService()
