"""
Tests pour l'authentification
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import create_test_user_data


class TestRegister:
    """Tests pour l'inscription"""

    def test_register_success(self, client: TestClient, mock_email_service):
        """Test inscription reussie"""
        user_data = create_test_user_data()
        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["is_verified"] is False
        assert "hashed_password" not in data
        assert len(mock_email_service) == 1  # Email envoye

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test inscription avec email existant"""
        user_data = create_test_user_data(
            username="different",
            email=test_user.email
        )
        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """Test inscription avec username existant"""
        user_data = create_test_user_data(
            username=test_user.username,
            email="different@example.com"
        )
        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already taken" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Test inscription avec email invalide"""
        user_data = create_test_user_data(email="invalid-email")
        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 422

    def test_register_weak_password(self, client: TestClient):
        """Test inscription avec mot de passe faible"""
        user_data = create_test_user_data(password="weak")
        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 422

    def test_register_missing_fields(self, client: TestClient):
        """Test inscription avec champs manquants"""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com"
        })

        assert response.status_code == 422


class TestLogin:
    """Tests pour la connexion"""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test connexion reussie"""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test connexion avec mauvais mot de passe"""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "WrongPassword123!"
        })

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test connexion avec utilisateur inexistant"""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "Test123!"
        })

        assert response.status_code == 401

    def test_login_unverified_user(self, client: TestClient, test_user_unverified: User):
        """Test connexion avec utilisateur non verifie"""
        response = client.post("/api/auth/login", json={
            "email": test_user_unverified.email,
            "password": "Test123!"
        })

        # Peut se connecter mais doit verifier email
        assert response.status_code == 200

    def test_login_inactive_user(self, client: TestClient, test_user: User, db_session: Session):
        """Test connexion avec utilisateur desactive"""
        test_user.is_active = False
        db_session.commit()

        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })

        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()


class TestVerifyEmail:
    """Tests pour la verification d'email"""

    def test_verify_email_success(
        self,
        client: TestClient,
        test_user_unverified: User,
        db_session: Session
    ):
        """Test verification d'email reussie"""
        from app.utils.security import create_verification_token

        token = create_verification_token(test_user_unverified.email)
        response = client.post("/api/auth/verify-email", json={
            "token": token
        })

        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

        # Verifier que l'utilisateur est maintenant verifie
        db_session.refresh(test_user_unverified)
        assert test_user_unverified.is_verified is True

    def test_verify_email_invalid_token(self, client: TestClient):
        """Test verification avec token invalide"""
        response = client.post("/api/auth/verify-email", json={
            "token": "invalid-token"
        })

        assert response.status_code == 400

    def test_verify_email_already_verified(self, client: TestClient, test_user: User):
        """Test verification d'un utilisateur deja verifie"""
        from app.utils.security import create_verification_token

        token = create_verification_token(test_user.email)
        response = client.post("/api/auth/verify-email", json={
            "token": token
        })

        assert response.status_code == 400
        assert "already verified" in response.json()["detail"].lower()


class TestForgotPassword:
    """Tests pour la reinitialisation de mot de passe"""

    def test_forgot_password_success(
        self,
        client: TestClient,
        test_user: User,
        mock_email_service
    ):
        """Test demande de reinitialisation reussie"""
        response = client.post("/api/auth/forgot-password", json={
            "email": test_user.email
        })

        assert response.status_code == 200
        assert "sent" in response.json()["message"].lower()
        assert len(mock_email_service) == 1

    def test_forgot_password_nonexistent_email(self, client: TestClient):
        """Test avec email inexistant"""
        response = client.post("/api/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })

        # Retourne toujours 200 pour eviter enumeration
        assert response.status_code == 200

    def test_reset_password_success(
        self,
        client: TestClient,
        test_user: User,
        db_session: Session
    ):
        """Test reinitialisation de mot de passe reussie"""
        from app.utils.security import create_reset_token

        token = create_reset_token(test_user.email)
        new_password = "NewPassword123!"

        response = client.post("/api/auth/reset-password", json={
            "token": token,
            "new_password": new_password
        })

        assert response.status_code == 200

        # Verifier que le nouveau mot de passe fonctionne
        login_response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": new_password
        })
        assert login_response.status_code == 200

    def test_reset_password_invalid_token(self, client: TestClient):
        """Test reinitialisation avec token invalide"""
        response = client.post("/api/auth/reset-password", json={
            "token": "invalid-token",
            "new_password": "NewPassword123!"
        })

        assert response.status_code == 400


class TestRefreshToken:
    """Tests pour le rafraichissement de token"""

    def test_refresh_token_success(self, client: TestClient, test_user: User):
        """Test rafraichissement de token reussi"""
        # Se connecter d'abord
        login_response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })
        refresh_token = login_response.json()["refresh_token"]

        # Rafraichir le token
        response = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_invalid(self, client: TestClient):
        """Test rafraichissement avec token invalide"""
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "invalid-token"
        })

        assert response.status_code == 401


class TestResendVerification:
    """Tests pour le renvoi d'email de verification"""

    def test_resend_verification_success(
        self,
        client: TestClient,
        test_user_unverified: User,
        mock_email_service
    ):
        """Test renvoi d'email de verification"""
        response = client.post("/api/auth/resend-verification", json={
            "email": test_user_unverified.email
        })

        assert response.status_code == 200
        assert len(mock_email_service) == 1

    def test_resend_verification_already_verified(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test renvoi pour utilisateur deja verifie"""
        response = client.post("/api/auth/resend-verification", json={
            "email": test_user.email
        })

        assert response.status_code == 400
        assert "already verified" in response.json()["detail"].lower()

    def test_resend_verification_nonexistent_user(self, client: TestClient):
        """Test renvoi pour utilisateur inexistant"""
        response = client.post("/api/auth/resend-verification", json={
            "email": "nonexistent@example.com"
        })

        assert response.status_code == 404
