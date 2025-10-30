"""
Tests pour l'administration
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.challenge import Challenge
from app.models.log import Log


class TestAdminUsers:
    """Tests pour la gestion des utilisateurs par admin"""

    def test_get_all_users(
        self,
        client: TestClient,
        admin_headers: dict,
        test_user: User,
        test_admin: User
    ):
        """Test recuperation tous les utilisateurs"""
        response = client.get("/api/admin/users", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # Au moins admin et test_user

    def test_get_all_users_no_admin(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test acces sans droits admin"""
        response = client.get("/api/admin/users", headers=auth_headers)

        assert response.status_code == 403

    def test_get_user_by_id(
        self,
        client: TestClient,
        admin_headers: dict,
        test_user: User
    ):
        """Test recuperation utilisateur par ID"""
        response = client.get(
            f"/api/admin/users/{test_user.id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    def test_update_user(
        self,
        client: TestClient,
        admin_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test mise a jour utilisateur"""
        response = client.put(
            f"/api/admin/users/{test_user.id}",
            headers=admin_headers,
            json={"full_name": "Updated by Admin"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated by Admin"

    def test_deactivate_user(
        self,
        client: TestClient,
        admin_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test desactivation utilisateur"""
        response = client.patch(
            f"/api/admin/users/{test_user.id}/deactivate",
            headers=admin_headers
        )

        assert response.status_code == 200
        db_session.refresh(test_user)
        assert test_user.is_active is False

    def test_activate_user(
        self,
        client: TestClient,
        admin_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test activation utilisateur"""
        # Desactiver d'abord
        test_user.is_active = False
        db_session.commit()

        response = client.patch(
            f"/api/admin/users/{test_user.id}/activate",
            headers=admin_headers
        )

        assert response.status_code == 200
        db_session.refresh(test_user)
        assert test_user.is_active is True

    def test_delete_user(
        self,
        client: TestClient,
        admin_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test suppression utilisateur"""
        user_id = test_user.id
        response = client.delete(
            f"/api/admin/users/{user_id}",
            headers=admin_headers
        )

        assert response.status_code == 200


class TestAdminStats:
    """Tests pour les statistiques admin"""

    def test_get_overview_stats(
        self,
        client: TestClient,
        admin_headers: dict,
        test_user: User,
        test_activity,
        test_challenge
    ):
        """Test statistiques generales"""
        response = client.get("/api/admin/stats/overview", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_activities" in data
        assert "total_challenges" in data
        assert data["total_users"] >= 1

    def test_get_users_growth(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test croissance utilisateurs"""
        response = client.get("/api/admin/stats/users-growth", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_app_usage(
        self,
        client: TestClient,
        admin_headers: dict,
        test_activity
    ):
        """Test usage des applications"""
        response = client.get("/api/admin/stats/app-usage", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_stats_no_admin(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test statistiques sans droits admin"""
        response = client.get("/api/admin/stats/overview", headers=auth_headers)

        assert response.status_code == 403


class TestAdminChallenges:
    """Tests pour la gestion des challenges par admin"""

    def test_get_all_challenges(
        self,
        client: TestClient,
        admin_headers: dict,
        test_challenge: Challenge
    ):
        """Test recuperation tous les challenges"""
        response = client.get("/api/admin/challenges", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_delete_challenge(
        self,
        client: TestClient,
        admin_headers: dict,
        test_challenge: Challenge,
        db_session: Session
    ):
        """Test suppression challenge"""
        challenge_id = test_challenge.id
        response = client.delete(
            f"/api/admin/challenges/{challenge_id}",
            headers=admin_headers
        )

        assert response.status_code == 200


class TestAdminLogs:
    """Tests pour les logs admin"""

    def test_get_logs(
        self,
        client: TestClient,
        admin_headers: dict,
        db_session: Session
    ):
        """Test recuperation logs"""
        # Creer quelques logs
        log1 = Log(level="INFO", message="Test log 1", action="test")
        log2 = Log(level="ERROR", message="Test log 2", action="test")
        db_session.add_all([log1, log2])
        db_session.commit()

        response = client.get("/api/admin/logs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_logs_with_filters(
        self,
        client: TestClient,
        admin_headers: dict,
        db_session: Session
    ):
        """Test logs avec filtres"""
        response = client.get(
            "/api/admin/logs?level=ERROR&limit=10",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_log_stats(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test statistiques logs"""
        response = client.get("/api/admin/logs/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_logs" in data or isinstance(data, dict)

    def test_cleanup_logs(
        self,
        client: TestClient,
        admin_headers: dict,
        db_session: Session
    ):
        """Test nettoyage logs"""
        # Creer vieux logs
        from datetime import datetime, timedelta
        old_log = Log(
            level="INFO",
            message="Old log",
            action="test",
            created_at=datetime.now() - timedelta(days=100)
        )
        db_session.add(old_log)
        db_session.commit()

        response = client.delete(
            "/api/admin/logs/cleanup?days=90",
            headers=admin_headers
        )

        assert response.status_code == 200


class TestAdminSystemHealth:
    """Tests pour le health check admin"""

    def test_system_health(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test sante du systeme"""
        response = client.get("/api/admin/system/health", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "status" in data

    def test_system_health_no_admin(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test health check sans droits admin"""
        response = client.get("/api/admin/system/health", headers=auth_headers)

        assert response.status_code == 403


class TestAdminAuthorization:
    """Tests pour l'autorisation admin"""

    def test_admin_required_routes(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test toutes les routes admin avec user normal"""
        admin_routes = [
            "/api/admin/users",
            "/api/admin/stats/overview",
            "/api/admin/challenges",
            "/api/admin/logs",
            "/api/admin/system/health"
        ]

        for route in admin_routes:
            response = client.get(route, headers=auth_headers)
            assert response.status_code == 403, f"Route {route} should require admin"

    def test_admin_access_with_admin_role(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test acces admin avec role admin"""
        response = client.get("/api/admin/users", headers=admin_headers)

        assert response.status_code == 200
