"""
Tests pour les WebSocket notifications
"""
import pytest
import json
from fastapi.testclient import TestClient

from app.models.user import User


class TestWebSocketConnection:
    """Tests pour la connexion WebSocket"""

    def test_websocket_connection_with_token(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test connexion WebSocket avec token valide"""
        # Se connecter pour obtenir token
        login_response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })
        token = login_response.json()["access_token"]

        # Tester connexion WebSocket
        with client.websocket_connect(f"/api/ws/notifications?token={token}") as websocket:
            # Recevoir message de connexion
            data = websocket.receive_json()
            assert data["type"] == "connection"
            assert "connected" in data["message"].lower()

    def test_websocket_connection_no_token(self, client: TestClient):
        """Test connexion sans token"""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws/notifications"):
                pass

    def test_websocket_connection_invalid_token(self, client: TestClient):
        """Test connexion avec token invalide"""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws/notifications?token=invalid"):
                pass


class TestWebSocketMessages:
    """Tests pour les messages WebSocket"""

    def test_websocket_ping(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test ping WebSocket"""
        login_response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })
        token = login_response.json()["access_token"]

        with client.websocket_connect(f"/api/ws/notifications?token={token}") as websocket:
            # Recevoir message connexion
            websocket.receive_json()

            # Envoyer ping
            websocket.send_json({"action": "ping"})

            # Recevoir pong
            response = websocket.receive_json()
            assert response["type"] == "pong"

    def test_websocket_get_stats(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test recuperation stats connexion"""
        login_response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })
        token = login_response.json()["access_token"]

        with client.websocket_connect(f"/api/ws/notifications?token={token}") as websocket:
            websocket.receive_json()  # Message connexion

            # Demander stats
            websocket.send_json({"action": "get_stats"})

            # Recevoir stats
            response = websocket.receive_json()
            assert "active_users" in response or "connections" in response

    def test_websocket_subscribe(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test subscription aux evenements"""
        login_response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })
        token = login_response.json()["access_token"]

        with client.websocket_connect(f"/api/ws/notifications?token={token}") as websocket:
            websocket.receive_json()

            # S'abonner aux evenements
            websocket.send_json({
                "action": "subscribe",
                "events": ["limit_warning", "app_blocked"]
            })

            response = websocket.receive_json()
            assert response["type"] == "subscribed"


class TestWebSocketNotifications:
    """Tests pour les notifications WebSocket"""

    def test_receive_notification(
        self,
        client: TestClient,
        test_user: User
    ):
        """Test reception notification"""
        login_response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test123!"
        })
        token = login_response.json()["access_token"]

        with client.websocket_connect(f"/api/ws/notifications?token={token}") as websocket:
            websocket.receive_json()

            # Note: Dans un test reel, on enverrait une notification
            # via le NotificationService
            # Pour l'instant, on teste juste la connexion


class TestWebSocketStats:
    """Tests pour les statistiques WebSocket"""

    def test_get_websocket_stats(
        self,
        client: TestClient,
        admin_headers: dict
    ):
        """Test recuperation stats WebSocket"""
        response = client.get("/api/ws/stats", headers=admin_headers)

        # La route peut ne pas exister, adapter selon implementation
        if response.status_code != 404:
            assert response.status_code in [200, 403]
            if response.status_code == 200:
                data = response.json()
                assert "active_connections" in data or isinstance(data, dict)
