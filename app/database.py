"""
Configuration de la base de donn�es MySQL avec SQLAlchemy
G�re la connexion, la session et la base d�clarative
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Cr�ation de l'engine SQLAlchemy avec pool de connexions
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,  # Nombre de connexions � maintenir
    max_overflow=20,  # Connexions suppl�mentaires en cas de pic
    pool_pre_ping=True,  # V�rifie la connexion avant de l'utiliser
    pool_recycle=3600,  # Recycle les connexions apr�s 1 heure
    echo=settings.DEBUG,  # Log les requ�tes SQL en mode debug
)

# Configuration de la session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base pour les mod�les SQLAlchemy
Base = declarative_base()


# Event listener pour activer les foreign keys en SQLite (si utilis� en dev)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Active les contraintes de cl�s �trang�res pour SQLite"""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass  # Ignore si ce n'est pas SQLite
    finally:
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency pour obtenir une session de base de donn�es
    Utilis� avec FastAPI Depends()

    Usage:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            return db.query(User).all()

    Yields:
        Session: Session de base de donn�es SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialise la base de donn�es
    Cr�e toutes les tables si elles n'existent pas
    """
    try:
        # Import tous les mod�les pour que Base les connaisse
        from app.models import (
            User,
            Activity,
            Challenge,
            ChallengeParticipant,
            BlockedApp,
            Log
        )

        # Cr�e toutes les tables
        Base.metadata.create_all(bind=engine)
        logger.info(" Base de donn�es initialis�e avec succ�s")

    except Exception as e:
        logger.error(f"L Erreur lors de l'initialisation de la base de donn�es: {e}")
        raise


async def create_admin_user() -> None:
    """
    Cr�e l'utilisateur administrateur par d�faut s'il n'existe pas
    Appel� au d�marrage de l'application
    """
    from app.models import User, UserRole
    from app.utils.security import get_password_hash

    db = SessionLocal()
    try:
        # V�rifie si l'admin existe d�j�
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()

        if not admin:
            # Cr�e l'administrateur
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
            logger.info(f" Administrateur cr��: {settings.ADMIN_EMAIL}")
        else:
            logger.info(f"9  Administrateur existe d�j�: {settings.ADMIN_EMAIL}")

    except Exception as e:
        db.rollback()
        logger.error(f"L Erreur lors de la cr�ation de l'admin: {e}")
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    V�rifie la connexion � la base de donn�es

    Returns:
        bool: True si la connexion est r�ussie, False sinon
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info(" Connexion � la base de donn�es r�ussie")
        return True
    except Exception as e:
        logger.error(f"L Impossible de se connecter � la base de donn�es: {e}")
        return False
