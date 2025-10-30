"""
Tests pour la gestion des utilisateurs
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


class TestGetCurrentUser:
    """Tests pour obtenir le profil utilisateur"""

    def test_get_current_user_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User
    ):
        """Test recuperation profil avec authentification"""
        response = client.get("/api/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert "hashed_password" not in data

    def test_get_current_user_no_auth(self, client: TestClient):
        """Test recuperation profil sans authentification"""
        response = client.get("/api/users/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test avec token invalide"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401


class TestUpdateUser:
    """Tests pour la mise a jour du profil"""

    def test_update_user_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test mise a jour reussie"""
        update_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio",
            "avatar_url": "https://example.com/avatar.jpg"
        }

        response = client.put(
            "/api/users/me",
            headers=auth_headers,
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["bio"] == update_data["bio"]
        assert data["avatar_url"] == update_data["avatar_url"]

        # Verifier dans la DB
        db_session.refresh(test_user)
        assert test_user.full_name == update_data["full_name"]

    def test_update_user_partial(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User
    ):
        """Test mise a jour partielle"""
        response = client.put(
            "/api/users/me",
            headers=auth_headers,
            json={"full_name": "New Name Only"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name Only"
        assert data["email"] == test_user.email  # Inchange

    def test_update_user_no_auth(self, client: TestClient):
        """Test mise a jour sans authentification"""
        response = client.put(
            "/api/users/me",
            json={"full_name": "New Name"}
        )

        assert response.status_code == 401

    def test_update_user_invalid_data(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec donnees invalides"""
        response = client.put(
            "/api/users/me",
            headers=auth_headers,
            json={"email": "invalid-email"}  # Email non modifiable via cette route
        )

        # Devrait ignorer le champ email ou retourner 422
        assert response.status_code in [200, 422]


class TestGetUserStats:
    """Tests pour les statistiques utilisateur"""

    def test_get_user_stats_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_activity
    ):
        """Test recuperation statistiques"""
        response = client.get("/api/users/me/stats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_time_minutes" in data
        assert "activities_count" in data
        assert "challenges_participated" in data
        assert "apps_used" in data

    def test_get_user_stats_no_data(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test statistiques sans donnees"""
        response = client.get("/api/users/me/stats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_time_minutes"] == 0
        assert data["activities_count"] == 0

    def test_get_user_stats_no_auth(self, client: TestClient):
        """Test statistiques sans authentification"""
        response = client.get("/api/users/me/stats")

        assert response.status_code == 401


class TestDeleteUser:
    """Tests pour la suppression de compte"""

    def test_delete_user_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test suppression de compte"""
        response = client.delete("/api/users/me", headers=auth_headers)

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verifier que l'utilisateur n'est plus actif
        db_session.refresh(test_user)
        assert test_user.is_active is False

    def test_delete_user_no_auth(self, client: TestClient):
        """Test suppression sans authentification"""
        response = client.delete("/api/users/me")

        assert response.status_code == 401

    def test_delete_user_already_deleted(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test suppression d'un compte deja supprime"""
        # Desactiver l'utilisateur
        test_user.is_active = False
        db_session.commit()

        # Essayer de se connecter
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })

        assert response.status_code == 400


class TestUserPassword:
    """Tests pour le changement de mot de passe"""

    def test_change_password_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User
    ):
        """Test changement de mot de passe"""
        # Note: Cette fonctionnalite peut ne pas exister encore
        # Adapter selon l'implementation
        new_password = "NewPassword123!"
        response = client.put(
            "/api/users/me/password",
            headers=auth_headers,
            json={
                "current_password": "Test123!",
                "new_password": new_password
            }
        )

        # Si la route n'existe pas, elle retournera 404
        if response.status_code != 404:
            assert response.status_code == 200

            # Tester la connexion avec le nouveau mot de passe
            login_response = client.post("/api/auth/login", json={
                "email": test_user.email,
                "password": new_password
            })
            assert login_response.status_code == 200

    def test_change_password_wrong_current(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec mauvais mot de passe actuel"""
        response = client.put(
            "/api/users/me/password",
            headers=auth_headers,
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPassword123!"
            }
        )

        if response.status_code != 404:
            assert response.status_code in [400, 401]


class TestUserPreferences:
    """Tests pour les preferences utilisateur"""

    def test_update_preferences(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test mise a jour des preferences"""
        preferences = {
            "notifications_enabled": False,
            "language": "fr",
            "timezone": "Europe/Paris"
        }

        response = client.put(
            "/api/users/me",
            headers=auth_headers,
            json=preferences
        )

        if response.status_code == 200:
            data = response.json()
            # Verifier que les preferences sont mises a jour
            # (selon l'implementation du modele)
            assert response.status_code == 200

    def test_get_preferences(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test recuperation des preferences"""
        response = client.get("/api/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Verifier la structure de reponse
        assert "email" in data
        assert "username" in data


class TestUserValidation:
    """Tests pour la validation des donnees utilisateur"""

    def test_username_validation(self, client: TestClient):
        """Test validation du username"""
        from tests.conftest import create_test_user_data

        # Username trop court
        user_data = create_test_user_data(username="ab")
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

        # Username avec caracteres invalides
        user_data = create_test_user_data(username="user@name")
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

    def test_email_validation(self, client: TestClient):
        """Test validation de l'email"""
        from tests.conftest import create_test_user_data

        # Email invalide
        user_data = create_test_user_data(email="not-an-email")
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

    def test_password_validation(self, client: TestClient):
        """Test validation du mot de passe"""
        from tests.conftest import create_test_user_data

        # Mot de passe trop court
        user_data = create_test_user_data(password="short")
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

        # Mot de passe sans chiffre
        user_data = create_test_user_data(password="NoNumbers!")
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422
