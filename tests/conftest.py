"""
Configuration pytest et fixtures pour les tests
"""
import asyncio
import pytest
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.activity import Activity
from app.models.challenge import Challenge, ChallengeParticipant
from app.models.blocked_app import BlockedApp
from app.models.log import Log
from app.utils.security import hash_password
from app.config import settings


# Base de donnees de test en memoire
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Activer les foreign keys pour SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Cree une session de base de donnees pour les tests
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Cree un client de test FastAPI
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Cree un utilisateur de test
    """
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("Test123!"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session: Session) -> User:
    """
    Cree un administrateur de test
    """
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("Admin123!"),
        full_name="Admin User",
        is_active=True,
        is_verified=True,
        role="admin"
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_user_unverified(db_session: Session) -> User:
    """
    Cree un utilisateur non verifie
    """
    user = User(
        username="unverified",
        email="unverified@example.com",
        hashed_password=hash_password("Test123!"),
        full_name="Unverified User",
        is_active=True,
        is_verified=False,
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client: TestClient, test_user: User) -> dict:
    """
    Retourne les headers d'authentification pour un utilisateur
    """
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test123!"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client: TestClient, test_admin: User) -> dict:
    """
    Retourne les headers d'authentification pour un admin
    """
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Admin123!"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_activity(db_session: Session, test_user: User) -> Activity:
    """
    Cree une activite de test
    """
    from datetime import date
    activity = Activity(
        user_id=test_user.id,
        app_name="Instagram",
        app_package="com.instagram.android",
        duration_minutes=30.0,
        activity_date=date.today()
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)
    return activity


@pytest.fixture
def test_blocked_app(db_session: Session, test_user: User) -> BlockedApp:
    """
    Cree une application bloquee de test
    """
    blocked = BlockedApp(
        user_id=test_user.id,
        app_name="Instagram",
        app_package="com.instagram.android",
        daily_limit_minutes=60,
        is_active=True,
        time_used_today=0
    )
    db_session.add(blocked)
    db_session.commit()
    db_session.refresh(blocked)
    return blocked


@pytest.fixture
def test_challenge(db_session: Session, test_user: User) -> Challenge:
    """
    Cree un challenge de test
    """
    from datetime import date, timedelta
    challenge = Challenge(
        name="Test Challenge",
        description="Test challenge description",
        creator_id=test_user.id,
        target_apps="Instagram,TikTok",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        is_public=True,
        is_active=True
    )
    db_session.add(challenge)
    db_session.commit()
    db_session.refresh(challenge)

    # Ajouter le createur comme participant
    participant = ChallengeParticipant(
        challenge_id=challenge.id,
        user_id=test_user.id,
        score=0
    )
    db_session.add(participant)
    db_session.commit()

    return challenge


@pytest.fixture(scope="session")
def event_loop():
    """
    Cree un event loop pour les tests asynchrones
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """
    Mock du service Redis pour les tests
    """
    class MockRedis:
        def __init__(self):
            self.data = {}

        async def get(self, key: str):
            return self.data.get(key)

        async def set(self, key: str, value: str, ex: int = None):
            self.data[key] = value
            return True

        async def setex(self, key: str, time: int, value: str):
            self.data[key] = value
            return True

        async def delete(self, *keys):
            for key in keys:
                self.data.pop(key, None)
            return len(keys)

        async def keys(self, pattern: str):
            import fnmatch
            return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]

        async def exists(self, key: str):
            return 1 if key in self.data else 0

        async def close(self):
            pass

    return MockRedis()


@pytest.fixture
def mock_email_service(monkeypatch):
    """
    Mock du service d'email pour les tests
    """
    sent_emails = []

    async def mock_send_email(*args, **kwargs):
        sent_emails.append({"args": args, "kwargs": kwargs})
        return True

    from app.services import email_service
    monkeypatch.setattr(email_service, "send_verification_email", mock_send_email)
    monkeypatch.setattr(email_service, "send_password_reset_email", mock_send_email)
    monkeypatch.setattr(email_service, "send_welcome_email", mock_send_email)

    return sent_emails


# Helpers pour les tests
def create_test_user_data(
    username: str = "newuser",
    email: str = "newuser@example.com",
    password: str = "Test123!",
    full_name: str = "New User"
) -> dict:
    """
    Cree des donnees de test pour un utilisateur
    """
    return {
        "username": username,
        "email": email,
        "password": password,
        "full_name": full_name
    }


def create_test_activity_data(
    app_name: str = "Instagram",
    app_package: str = "com.instagram.android",
    duration_minutes: float = 30.0
) -> dict:
    """
    Cree des donnees de test pour une activite
    """
    from datetime import date
    return {
        "app_name": app_name,
        "app_package": app_package,
        "duration_minutes": duration_minutes,
        "activity_date": str(date.today())
    }


def create_test_challenge_data(
    name: str = "New Challenge",
    description: str = "Challenge description",
    target_apps: str = "Instagram,TikTok",
    is_public: bool = True
) -> dict:
    """
    Cree des donnees de test pour un challenge
    """
    from datetime import date, timedelta
    return {
        "name": name,
        "description": description,
        "target_apps": target_apps,
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=7)),
        "is_public": is_public
    }


def create_test_blocked_app_data(
    app_name: str = "Instagram",
    app_package: str = "com.instagram.android",
    daily_limit_minutes: int = 60
) -> dict:
    """
    Cree des donnees de test pour une app bloquee
    """
    return {
        "app_name": app_name,
        "app_package": app_package,
        "daily_limit_minutes": daily_limit_minutes,
        "is_active": True
    }
