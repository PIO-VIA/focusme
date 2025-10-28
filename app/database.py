"""
Configuration de la base de données MySQL avec SQLAlchemy
Gère la connexion, la session et la base déclarative
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Création de l'engine SQLAlchemy avec pool de connexions
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # Nombre de connexions à maintenir
    max_overflow=20,  # Connexions supplémentaires en cas de pic
    pool_pre_ping=True,  # Vérifie la connexion avant de l'utiliser
    pool_recycle=3600,  # Recycle les connexions après 1 heure
    echo=settings.DEBUG,  # Log les requêtes SQL en mode debug
)

# Configuration de la session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base pour les modèles SQLAlchemy
Base = declarative_base()


# Event listener pour activer les foreign keys en SQLite (si utilisé en dev)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Active les contraintes de clés étrangères pour SQLite"""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass  # Ignore si ce n'est pas SQLite
    finally:
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency pour obtenir une session de base de données
    Utilisé avec FastAPI Depends()

    Usage:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            return db.query(User).all()

    Yields:
        Session: Session de base de données SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialise la base de données
    Crée toutes les tables si elles n'existent pas
    """
    try:
        # Import tous les modèles pour que Base les connaisse
        from app.models import (
            User,
            Activity,
            Challenge,
            ChallengeParticipant,
            BlockedApp,
            Log
        )

        # Crée toutes les tables
        Base.metadata.create_all(bind=engine)
        logger.info(" Base de données initialisée avec succès")

    except Exception as e:
        logger.error(f"L Erreur lors de l'initialisation de la base de données: {e}")
        raise


async def create_admin_user() -> None:
    """
    Crée l'utilisateur administrateur par défaut s'il n'existe pas
    Appelé au démarrage de l'application
    """
    from app.models import User, UserRole
    from app.utils.security import get_password_hash

    db = SessionLocal()
    try:
        # Vérifie si l'admin existe déjà
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()

        if not admin:
            # Crée l'administrateur
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                full_name="Administrateur",
                role=UserRole.ADMIN,
                is_verified=True,
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info(f" Administrateur créé: {settings.ADMIN_EMAIL}")
        else:
            logger.info(f"9  Administrateur existe déjà: {settings.ADMIN_EMAIL}")

    except Exception as e:
        db.rollback()
        logger.error(f"L Erreur lors de la création de l'admin: {e}")
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Vérifie la connexion à la base de données

    Returns:
        bool: True si la connexion est réussie, False sinon
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info(" Connexion à la base de données réussie")
        return True
    except Exception as e:
        logger.error(f"L Impossible de se connecter à la base de données: {e}")
        return False
