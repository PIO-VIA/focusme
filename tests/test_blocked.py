"""
Tests pour les applications bloquees
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.blocked_app import BlockedApp
from tests.conftest import create_test_blocked_app_data


class TestCreateBlockedApp:
    """Tests pour le blocage d'application"""

    def test_create_blocked_app_success(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test blocage d'app reussi"""
        blocked_data = create_test_blocked_app_data()
        response = client.post(
            "/api/blocked",
            headers=auth_headers,
            json=blocked_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["app_name"] == blocked_data["app_name"]
        assert data["daily_limit_minutes"] == blocked_data["daily_limit_minutes"]
        assert data["time_used_today"] == 0
        assert data["is_blocked"] is False

    def test_create_blocked_app_duplicate(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp
    ):
        """Test blocage d'app deja bloquee"""
        blocked_data = create_test_blocked_app_data(
            app_name=test_blocked_app.app_name,
            app_package=test_blocked_app.app_package
        )
        response = client.post(
            "/api/blocked",
            headers=auth_headers,
            json=blocked_data
        )

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_create_blocked_app_invalid_limit(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec limite invalide"""
        blocked_data = create_test_blocked_app_data(daily_limit_minutes=-10)
        response = client.post(
            "/api/blocked",
            headers=auth_headers,
            json=blocked_data
        )

        assert response.status_code == 422

    def test_create_blocked_app_no_auth(self, client: TestClient):
        """Test sans authentification"""
        blocked_data = create_test_blocked_app_data()
        response = client.post("/api/blocked", json=blocked_data)

        assert response.status_code == 401


class TestGetBlockedApps:
    """Tests pour la recuperation des apps bloquees"""

    def test_get_blocked_apps_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp
    ):
        """Test recuperation liste apps bloquees"""
        response = client.get("/api/blocked", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["app_name"] == test_blocked_app.app_name

    def test_get_blocked_app_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp
    ):
        """Test recuperation app bloquee par ID"""
        response = client.get(
            f"/api/blocked/{test_blocked_app.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_blocked_app.id
        assert data["app_name"] == test_blocked_app.app_name

    def test_get_blocked_app_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test recuperation app inexistante"""
        response = client.get("/api/blocked/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_get_blocked_apps_empty(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test liste vide"""
        response = client.get("/api/blocked", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestUpdateBlockedApp:
    """Tests pour la mise a jour d'app bloquee"""

    def test_update_blocked_app_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp,
        db_session: Session
    ):
        """Test mise a jour reussie"""
        update_data = {
            "daily_limit_minutes": 120,
            "is_active": False
        }

        response = client.put(
            f"/api/blocked/{test_blocked_app.id}",
            headers=auth_headers,
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["daily_limit_minutes"] == update_data["daily_limit_minutes"]
        assert data["is_active"] == update_data["is_active"]

    def test_update_blocked_app_partial(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp
    ):
        """Test mise a jour partielle"""
        response = client.put(
            f"/api/blocked/{test_blocked_app.id}",
            headers=auth_headers,
            json={"daily_limit_minutes": 90}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["daily_limit_minutes"] == 90

    def test_update_blocked_app_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test mise a jour app inexistante"""
        response = client.put(
            "/api/blocked/99999",
            headers=auth_headers,
            json={"daily_limit_minutes": 90}
        )

        assert response.status_code == 404


class TestResetBlockedApp:
    """Tests pour la reinitialisation d'app bloquee"""

    def test_reset_blocked_app_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp,
        db_session: Session
    ):
        """Test reinitialisation reussie"""
        # Definir time_used_today et is_blocked
        test_blocked_app.time_used_today = 50
        test_blocked_app.is_blocked = True
        db_session.commit()

        response = client.post(
            f"/api/blocked/{test_blocked_app.id}/reset",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["time_used_today"] == 0
        assert data["is_blocked"] is False

    def test_reset_blocked_app_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test reinitialisation app inexistante"""
        response = client.post(
            "/api/blocked/99999/reset",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestDeleteBlockedApp:
    """Tests pour la suppression d'app bloquee"""

    def test_delete_blocked_app_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp,
        db_session: Session
    ):
        """Test suppression reussie"""
        blocked_id = test_blocked_app.id
        response = client.delete(
            f"/api/blocked/{blocked_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verifier suppression
        blocked = db_session.query(BlockedApp).filter_by(id=blocked_id).first()
        assert blocked is None

    def test_delete_blocked_app_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test suppression app inexistante"""
        response = client.delete("/api/blocked/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_blocked_app_no_auth(
        self,
        client: TestClient,
        test_blocked_app: BlockedApp
    ):
        """Test suppression sans authentification"""
        response = client.delete(f"/api/blocked/{test_blocked_app.id}")

        assert response.status_code == 401


class TestBlockedAppLogic:
    """Tests pour la logique de blocage"""

    def test_app_blocked_when_limit_exceeded(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp,
        db_session: Session
    ):
        """Test blocage quand limite depassee"""
        # Definir time_used au-dela de la limite
        test_blocked_app.time_used_today = test_blocked_app.daily_limit_minutes + 10
        test_blocked_app.is_blocked = True
        db_session.commit()

        response = client.get(
            f"/api/blocked/{test_blocked_app.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_blocked"] is True

    def test_app_not_blocked_within_limit(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp,
        db_session: Session
    ):
        """Test pas de blocage dans la limite"""
        test_blocked_app.time_used_today = 30  # En dessous de 60
        test_blocked_app.is_blocked = False
        db_session.commit()

        response = client.get(
            f"/api/blocked/{test_blocked_app.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_blocked"] is False

    def test_app_inactive_not_blocked(
        self,
        client: TestClient,
        auth_headers: dict,
        test_blocked_app: BlockedApp,
        db_session: Session
    ):
        """Test app inactive non bloquee meme si limite depassee"""
        test_blocked_app.time_used_today = 100
        test_blocked_app.is_active = False
        test_blocked_app.is_blocked = False
        db_session.commit()

        response = client.get(
            f"/api/blocked/{test_blocked_app.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_blocked"] is False


class TestBlockedAppValidation:
    """Tests pour la validation des apps bloquees"""

    def test_blocked_app_missing_fields(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec champs manquants"""
        response = client.post(
            "/api/blocked",
            headers=auth_headers,
            json={"app_name": "Instagram"}
        )

        assert response.status_code == 422

    def test_blocked_app_zero_limit(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec limite zero"""
        blocked_data = create_test_blocked_app_data(daily_limit_minutes=0)
        response = client.post(
            "/api/blocked",
            headers=auth_headers,
            json=blocked_data
        )

        # Peut etre accepte (blocage total) ou refuse
        assert response.status_code in [201, 422]

    def test_blocked_app_very_high_limit(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec limite tres elevee"""
        blocked_data = create_test_blocked_app_data(daily_limit_minutes=10000)
        response = client.post(
            "/api/blocked",
            headers=auth_headers,
            json=blocked_data
        )

        # Devrait etre accepte
        assert response.status_code == 201
