"""
Configuration de l'application Focus API
Charge les variables d'environnement et fournit les param�tres globaux
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, validator
import secrets


class Settings(BaseSettings):
    """Classe de configuration principale utilisant Pydantic Settings"""

    # Configuration de l'application
    APP_NAME: str = "Focus API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Configuration de la base de donn�es
    DATABASE_URL: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str
    DB_NAME: str = "focus_db"

    # Configuration JWT
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Configuration Email
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr = "noreply@focusapp.com"
    MAIL_FROM_NAME: str = "Focus App"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    USE_CREDENTIALS: bool = True

    # URLs Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_VERIFY_URL: str = "http://localhost:3000/verify-email"
    PASSWORD_RESET_URL: str = "http://localhost:3000/reset-password"

    # Configuration CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:19006"
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        """Convertit une cha�ne JSON en liste pour les origines CORS"""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Admin par d�faut
    ADMIN_EMAIL: EmailStr = "admin@focusapp.com"
    ADMIN_PASSWORD: str = "AdminSecure123!"
    ADMIN_USERNAME: str = "admin"

    # Configuration des challenges
    CHALLENGE_DURATION_DAYS: int = 7
    REMINDER_TIME: str = "09:00"

    # Limite par d�faut (en minutes)
    DEFAULT_DAILY_LIMIT: int = 120

    # Configuration Redis Cache
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 5 minutes par defaut

    # Configuration Prometheus
    METRICS_ENABLED: bool = True
    METRICS_ENDPOINT: str = "/metrics"

    # Configuration OAuth Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    OAUTH_ENABLED: bool = False

    # Configuration WebSocket
    WEBSOCKET_ENABLED: bool = True
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # secondes

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )


# Instance globale des settings
settings = Settings()


# Configuration du logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}
