"""
Tests pour les challenges
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.challenge import Challenge, ChallengeParticipant
from tests.conftest import create_test_challenge_data


class TestCreateChallenge:
    """Tests pour la creation de challenge"""

    def test_create_challenge_success(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """Test creation challenge reussie"""
        challenge_data = create_test_challenge_data()
        response = client.post(
            "/api/challenges",
            headers=auth_headers,
            json=challenge_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == challenge_data["name"]
        assert data["is_public"] == challenge_data["is_public"]
        assert "id" in data
        assert "invitation_code" in data

    def test_create_private_challenge(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test creation challenge prive"""
        challenge_data = create_test_challenge_data(is_public=False)
        response = client.post(
            "/api/challenges",
            headers=auth_headers,
            json=challenge_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_public"] is False
        assert data["invitation_code"] is not None

    def test_create_challenge_invalid_dates(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec dates invalides"""
        challenge_data = create_test_challenge_data()
        # Date fin avant date debut
        challenge_data["end_date"] = str(date.today() - timedelta(days=1))

        response = client.post(
            "/api/challenges",
            headers=auth_headers,
            json=challenge_data
        )

        assert response.status_code == 400

    def test_create_challenge_no_auth(self, client: TestClient):
        """Test sans authentification"""
        challenge_data = create_test_challenge_data()
        response = client.post("/api/challenges", json=challenge_data)

        assert response.status_code == 401


class TestGetChallenges:
    """Tests pour la recuperation des challenges"""

    def test_get_public_challenges(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge
    ):
        """Test recuperation challenges publics"""
        response = client.get("/api/challenges", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_my_challenges(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge
    ):
        """Test recuperation mes challenges"""
        response = client.get("/api/challenges/my-challenges", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_challenge_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge
    ):
        """Test recuperation challenge par ID"""
        response = client.get(
            f"/api/challenges/{test_challenge.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_challenge.id
        assert data["name"] == test_challenge.name


class TestJoinChallenge:
    """Tests pour rejoindre un challenge"""

    def test_join_public_challenge(
        self,
        client: TestClient,
        test_user: User,
        test_admin: User,
        test_challenge: Challenge,
        db_session: Session
    ):
        """Test rejoindre challenge public"""
        # Se connecter avec un autre utilisateur
        login_response = client.post("/api/auth/login", json={
            "email": test_admin.email,
            "password": "Admin123!"
        })
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        response = client.post(
            f"/api/challenges/{test_challenge.id}/join",
            headers=headers
        )

        assert response.status_code == 200
        assert "joined" in response.json()["message"].lower()

    def test_join_private_challenge_with_code(
        self,
        client: TestClient,
        test_user: User,
        test_admin: User,
        db_session: Session
    ):
        """Test rejoindre challenge prive avec code"""
        # Creer challenge prive
        challenge = Challenge(
            name="Private Challenge",
            description="Private challenge",
            creator_id=test_user.id,
            target_apps="Instagram",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            is_public=False,
            invitation_code="TESTCODE"
        )
        db_session.add(challenge)
        db_session.commit()

        # Se connecter avec admin
        login_response = client.post("/api/auth/login", json={
            "email": test_admin.email,
            "password": "Admin123!"
        })
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Rejoindre avec code
        response = client.post(
            f"/api/challenges/{challenge.id}/join",
            headers=headers,
            json={"invitation_code": "TESTCODE"}
        )

        assert response.status_code == 200

    def test_join_challenge_already_member(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge
    ):
        """Test rejoindre challenge deja membre"""
        response = client.post(
            f"/api/challenges/{test_challenge.id}/join",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()


class TestLeaveChallenge:
    """Tests pour quitter un challenge"""

    def test_leave_challenge_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge,
        db_session: Session
    ):
        """Test quitter challenge"""
        response = client.post(
            f"/api/challenges/{test_challenge.id}/leave",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_leave_challenge_not_member(
        self,
        client: TestClient,
        test_admin: User,
        test_challenge: Challenge
    ):
        """Test quitter challenge dont on n'est pas membre"""
        login_response = client.post("/api/auth/login", json={
            "email": test_admin.email,
            "password": "Admin123!"
        })
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        response = client.post(
            f"/api/challenges/{test_challenge.id}/leave",
            headers=headers
        )

        assert response.status_code == 400


class TestChallengeLeaderboard:
    """Tests pour le classement du challenge"""

    def test_get_leaderboard(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge
    ):
        """Test recuperation classement"""
        response = client.get(
            f"/api/challenges/{test_challenge.id}/leaderboard",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_leaderboard_ordering(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge,
        test_admin: User,
        db_session: Session
    ):
        """Test ordre du classement"""
        # Ajouter admin au challenge avec score
        participant = ChallengeParticipant(
            challenge_id=test_challenge.id,
            user_id=test_admin.id,
            score=100
        )
        db_session.add(participant)
        db_session.commit()

        response = client.get(
            f"/api/challenges/{test_challenge.id}/leaderboard",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Verifier ordre decroissant des scores
        scores = [p["score"] for p in data]
        assert scores == sorted(scores, reverse=True)


class TestDeleteChallenge:
    """Tests pour la suppression de challenge"""

    def test_delete_challenge_as_creator(
        self,
        client: TestClient,
        auth_headers: dict,
        test_challenge: Challenge,
        db_session: Session
    ):
        """Test suppression par createur"""
        challenge_id = test_challenge.id
        response = client.delete(
            f"/api/challenges/{challenge_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_delete_challenge_not_creator(
        self,
        client: TestClient,
        test_admin: User,
        test_challenge: Challenge
    ):
        """Test suppression par non-createur"""
        login_response = client.post("/api/auth/login", json={
            "email": test_admin.email,
            "password": "Admin123!"
        })
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        response = client.delete(
            f"/api/challenges/{test_challenge.id}",
            headers=headers
        )

        assert response.status_code == 403


class TestChallengeValidation:
    """Tests pour la validation des challenges"""

    def test_challenge_missing_fields(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec champs manquants"""
        response = client.post(
            "/api/challenges",
            headers=auth_headers,
            json={"name": "Test Challenge"}  # Champs manquants
        )

        assert response.status_code == 422

    def test_challenge_empty_name(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec nom vide"""
        challenge_data = create_test_challenge_data(name="")
        response = client.post(
            "/api/challenges",
            headers=auth_headers,
            json=challenge_data
        )

        assert response.status_code == 422

    def test_challenge_empty_target_apps(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test sans apps cibles"""
        challenge_data = create_test_challenge_data(target_apps="")
        response = client.post(
            "/api/challenges",
            headers=auth_headers,
            json=challenge_data
        )

        assert response.status_code == 422
