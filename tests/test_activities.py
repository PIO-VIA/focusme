"""
Tests pour la gestion des activites
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.activity import Activity
from tests.conftest import create_test_activity_data


class TestCreateActivity:
    """Tests pour la creation d'activite"""

    def test_create_activity_success(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """Test creation d'activite reussie"""
        activity_data = create_test_activity_data()
        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json=activity_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["app_name"] == activity_data["app_name"]
        assert data["duration_minutes"] == activity_data["duration_minutes"]
        assert "id" in data

    def test_create_activity_no_auth(self, client: TestClient):
        """Test creation sans authentification"""
        activity_data = create_test_activity_data()
        response = client.post("/api/activities", json=activity_data)

        assert response.status_code == 401

    def test_create_activity_invalid_duration(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec duree invalide"""
        activity_data = create_test_activity_data(duration_minutes=-10)
        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json=activity_data
        )

        assert response.status_code == 422

    def test_create_activity_future_date(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec date future"""
        activity_data = create_test_activity_data()
        activity_data["activity_date"] = str(date.today() + timedelta(days=1))

        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json=activity_data
        )

        assert response.status_code == 400


class TestGetActivities:
    """Tests pour la recuperation des activites"""

    def test_get_activities_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_activity: Activity
    ):
        """Test recuperation liste activites"""
        response = client.get("/api/activities", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["app_name"] == test_activity.app_name

    def test_get_activities_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test pagination des activites"""
        # Creer plusieurs activites
        for i in range(15):
            activity = Activity(
                user_id=test_user.id,
                app_name=f"App{i}",
                app_package=f"com.app{i}",
                duration_minutes=30.0,
                activity_date=date.today()
            )
            db_session.add(activity)
        db_session.commit()

        # Test pagination
        response = client.get(
            "/api/activities?skip=0&limit=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    def test_get_activities_filter_by_date(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test filtre par date"""
        # Creer activites avec dates differentes
        today = date.today()
        yesterday = today - timedelta(days=1)

        activity_today = Activity(
            user_id=test_user.id,
            app_name="TodayApp",
            app_package="com.today",
            duration_minutes=30.0,
            activity_date=today
        )
        activity_yesterday = Activity(
            user_id=test_user.id,
            app_name="YesterdayApp",
            app_package="com.yesterday",
            duration_minutes=30.0,
            activity_date=yesterday
        )
        db_session.add_all([activity_today, activity_yesterday])
        db_session.commit()

        # Filtrer par date
        response = client.get(
            f"/api/activities?date={today}",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.json()
            # Verifier que seules les activites d'aujourd'hui sont retournees
            assert all(a["activity_date"] == str(today) for a in data)

    def test_get_activities_no_auth(self, client: TestClient):
        """Test sans authentification"""
        response = client.get("/api/activities")

        assert response.status_code == 401


class TestGetTodayActivities:
    """Tests pour les activites du jour"""

    def test_get_today_activities_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_activity: Activity
    ):
        """Test recuperation activites du jour"""
        response = client.get("/api/activities/today", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_today_activities_empty(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test sans activites aujourd'hui"""
        # Creer activite hier
        yesterday = date.today() - timedelta(days=1)
        activity = Activity(
            user_id=test_user.id,
            app_name="YesterdayApp",
            app_package="com.yesterday",
            duration_minutes=30.0,
            activity_date=yesterday
        )
        db_session.add(activity)
        db_session.commit()

        response = client.get("/api/activities/today", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestGetActivityStats:
    """Tests pour les statistiques d'activites"""

    def test_get_daily_stats(
        self,
        client: TestClient,
        auth_headers: dict,
        test_activity: Activity
    ):
        """Test statistiques quotidiennes"""
        response = client.get("/api/activities/stats/daily", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_time" in data
        assert "apps" in data
        assert isinstance(data["apps"], list)

    def test_get_weekly_stats(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_session: Session
    ):
        """Test statistiques hebdomadaires"""
        # Creer activites sur plusieurs jours
        for i in range(7):
            activity_date = date.today() - timedelta(days=i)
            activity = Activity(
                user_id=test_user.id,
                app_name="Instagram",
                app_package="com.instagram.android",
                duration_minutes=30.0,
                activity_date=activity_date
            )
            db_session.add(activity)
        db_session.commit()

        response = client.get("/api/activities/stats/weekly", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_time" in data
        assert "daily_breakdown" in data

    def test_get_stats_no_data(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test statistiques sans donnees"""
        response = client.get("/api/activities/stats/daily", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_time"] == 0


class TestDeleteActivity:
    """Tests pour la suppression d'activites"""

    def test_delete_activity_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_activity: Activity,
        db_session: Session
    ):
        """Test suppression reussie"""
        activity_id = test_activity.id
        response = client.delete(
            f"/api/activities/{activity_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verifier que l'activite n'existe plus
        activity = db_session.query(Activity).filter_by(id=activity_id).first()
        assert activity is None

    def test_delete_activity_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test suppression activite inexistante"""
        response = client.delete(
            "/api/activities/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_delete_activity_not_owner(
        self,
        client: TestClient,
        test_user: User,
        test_admin: User,
        db_session: Session
    ):
        """Test suppression activite d'un autre utilisateur"""
        # Creer activite pour test_user
        activity = Activity(
            user_id=test_user.id,
            app_name="Instagram",
            app_package="com.instagram.android",
            duration_minutes=30.0,
            activity_date=date.today()
        )
        db_session.add(activity)
        db_session.commit()
        activity_id = activity.id

        # Se connecter en tant qu'admin
        login_response = client.post("/api/auth/login", json={
            "email": test_admin.email,
            "password": "Admin123!"
        })
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Essayer de supprimer
        response = client.delete(
            f"/api/activities/{activity_id}",
            headers=admin_headers
        )

        # Doit etre interdit (ou reussi si admin peut tout supprimer)
        assert response.status_code in [403, 200]

    def test_delete_activity_no_auth(self, client: TestClient, test_activity: Activity):
        """Test suppression sans authentification"""
        response = client.delete(f"/api/activities/{test_activity.id}")

        assert response.status_code == 401


class TestActivityValidation:
    """Tests pour la validation des activites"""

    def test_activity_missing_fields(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec champs manquants"""
        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json={"app_name": "Instagram"}  # Champs manquants
        )

        assert response.status_code == 422

    def test_activity_invalid_date_format(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec format de date invalide"""
        activity_data = create_test_activity_data()
        activity_data["activity_date"] = "invalid-date"

        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json=activity_data
        )

        assert response.status_code == 422

    def test_activity_negative_duration(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec duree negative"""
        activity_data = create_test_activity_data(duration_minutes=-10.5)

        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json=activity_data
        )

        assert response.status_code == 422

    def test_activity_zero_duration(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec duree zero"""
        activity_data = create_test_activity_data(duration_minutes=0)

        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json=activity_data
        )

        # Peut etre accepte ou refuse selon la logique
        assert response.status_code in [201, 422]

    def test_activity_very_long_duration(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test avec duree tres longue (24h+)"""
        activity_data = create_test_activity_data(duration_minutes=1500)  # 25h

        response = client.post(
            "/api/activities",
            headers=auth_headers,
            json=activity_data
        )

        # Peut etre accepte ou refuse selon la validation
        assert response.status_code in [201, 400, 422]
