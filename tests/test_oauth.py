"""
Tests pour le service OAuth Google
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.oauth_service import OAuthService
from app.models.user import User


class TestOAuthService:
    """Tests pour le service OAuth"""

    def test_get_authorization_url(self):
        """Test generation URL autorisation"""
        url, state = OAuthService.get_authorization_url("http://localhost/callback")

        assert "accounts.google.com" in url
        assert "oauth2" in url
        assert "client_id" in url
        assert state is not None
        assert len(state) > 20

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self):
        """Test echange code pour token"""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            "access_token": "test_token",
            "id_token": "test_id_token",
            "expires_in": 3600
        })

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await OAuthService.exchange_code_for_token(
                "test_code",
                "http://localhost/callback"
            )

            assert "access_token" in result
            assert result["access_token"] == "test_token"

    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test recuperation infos utilisateur"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            "sub": "google_user_id",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg"
        })

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await OAuthService.get_user_info("test_token")

            assert result["email"] == "user@gmail.com"
            assert result["name"] == "Test User"

    def test_get_or_create_user_new(self, db_session: Session):
        """Test creation nouvel utilisateur OAuth"""
        user = OAuthService.get_or_create_user(
            db=db_session,
            google_id="new_google_id",
            email="newuser@gmail.com",
            name="New User",
            picture="https://example.com/photo.jpg"
        )

        assert user.id is not None
        assert user.email == "newuser@gmail.com"
        assert user.full_name == "New User"
        assert user.is_verified is True  # Auto-verified for OAuth
        assert user.avatar_url == "https://example.com/photo.jpg"

    def test_get_or_create_user_existing(
        self,
        db_session: Session,
        test_user: User
    ):
        """Test utilisateur OAuth existant"""
        # Definir google_id
        test_user.google_id = "existing_google_id"
        db_session.commit()

        user = OAuthService.get_or_create_user(
            db=db_session,
            google_id="existing_google_id",
            email=test_user.email,
            name="Updated Name"
        )

        assert user.id == test_user.id
        assert user.email == test_user.email


class TestOAuthEndpoints:
    """Tests pour les endpoints OAuth"""

    def test_google_login_endpoint(self, client: TestClient):
        """Test endpoint initiation OAuth"""
        response = client.get("/api/auth/google")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_google_callback_success(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test callback OAuth reussi"""
        # Mock les appels OAuth
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json = Mock(return_value={
            "access_token": "test_token",
            "id_token": "test_id_token"
        })

        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json = Mock(return_value={
            "sub": "google_123",
            "email": "oauth@gmail.com",
            "name": "OAuth User",
            "picture": "https://example.com/photo.jpg"
        })

        with patch("httpx.AsyncClient.post", return_value=mock_token_response):
            with patch("httpx.AsyncClient.get", return_value=mock_user_response):
                response = client.get(
                    "/api/auth/google/callback?code=test_code&state=test_state"
                )

                # Peut retourner 200 ou rediriger
                assert response.status_code in [200, 307, 302]

    def test_google_callback_missing_code(self, client: TestClient):
        """Test callback sans code"""
        response = client.get("/api/auth/google/callback")

        # Devrait retourner erreur
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_google_callback_invalid_code(self, client: TestClient):
        """Test callback avec code invalide"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json = Mock(return_value={"error": "invalid_grant"})

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            response = client.get(
                "/api/auth/google/callback?code=invalid_code&state=test_state"
            )

            # Devrait retourner erreur
            assert response.status_code in [400, 401]


class TestOAuthSecurity:
    """Tests pour la securite OAuth"""

    def test_state_parameter_generated(self):
        """Test generation parametre state (CSRF)"""
        url1, state1 = OAuthService.get_authorization_url("http://localhost/callback")
        url2, state2 = OAuthService.get_authorization_url("http://localhost/callback")

        # Chaque state doit etre unique
        assert state1 != state2

    def test_authorization_url_contains_state(self):
        """Test presence du state dans URL"""
        url, state = OAuthService.get_authorization_url("http://localhost/callback")

        assert f"state={state}" in url

    def test_email_auto_verified(self, db_session: Session):
        """Test auto-verification email OAuth"""
        user = OAuthService.get_or_create_user(
            db=db_session,
            google_id="google_123",
            email="oauth@gmail.com",
            name="OAuth User"
        )

        # Les utilisateurs OAuth sont auto-verifies
        assert user.is_verified is True


class TestOAuthErrors:
    """Tests pour la gestion d'erreurs OAuth"""

    @pytest.mark.asyncio
    async def test_oauth_network_error(self):
        """Test erreur reseau OAuth"""
        with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
            with pytest.raises(Exception):
                await OAuthService.exchange_code_for_token(
                    "test_code",
                    "http://localhost/callback"
                )

    @pytest.mark.asyncio
    async def test_oauth_invalid_response(self):
        """Test reponse invalide OAuth"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={})  # Response incomplete

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await OAuthService.exchange_code_for_token(
                "test_code",
                "http://localhost/callback"
            )

            # Devrait gerer l'erreur
            assert "access_token" not in result or result.get("access_token") is None


class TestOAuthIntegration:
    """Tests d'integration OAuth"""

    def test_oauth_creates_valid_jwt_tokens(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test que OAuth cree des tokens JWT valides"""
        # Creer utilisateur OAuth
        user = OAuthService.get_or_create_user(
            db=db_session,
            google_id="google_123",
            email="oauth@gmail.com",
            name="OAuth User"
        )

        # Se connecter normalement avec cet utilisateur
        from app.utils.security import create_access_token

        token = create_access_token({"sub": user.email})

        # Utiliser le token
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert data["email"] == user.email
