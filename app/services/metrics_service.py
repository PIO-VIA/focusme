"""
Service de metriques Prometheus
Collecte et expose les metriques de l'application
"""
import logging
from typing import Callable
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

from app.config import settings

logger = logging.getLogger(__name__)


# ========================
# METRIQUES PROMETHEUS
# ========================

# Informations sur l'application
app_info = Info('focus_api_info', 'Information about Focus API')
app_info.info({
    'version': settings.APP_VERSION,
    'name': settings.APP_NAME
})

# Requetes HTTP
http_requests_total = Counter(
    'focus_api_http_requests_total',
    'Total des requetes HTTP',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'focus_api_http_request_duration_seconds',
    'Duree des requetes HTTP en secondes',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'focus_api_http_requests_in_progress',
    'Nombre de requetes HTTP en cours',
    ['method', 'endpoint']
)

# Erreurs
http_errors_total = Counter(
    'focus_api_http_errors_total',
    'Total des erreurs HTTP',
    ['method', 'endpoint', 'error_type']
)

# Base de donnees
db_queries_total = Counter(
    'focus_api_db_queries_total',
    'Total des requetes en base de donnees',
    ['operation']
)

db_query_duration_seconds = Histogram(
    'focus_api_db_query_duration_seconds',
    'Duree des requetes en base de donnees',
    ['operation']
)

db_connections_active = Gauge(
    'focus_api_db_connections_active',
    'Nombre de connexions actives a la base de donnees'
)

# Cache Redis
cache_hits_total = Counter(
    'focus_api_cache_hits_total',
    'Total des hits de cache'
)

cache_misses_total = Counter(
    'focus_api_cache_misses_total',
    'Total des misses de cache'
)

cache_operations_duration_seconds = Histogram(
    'focus_api_cache_operations_duration_seconds',
    'Duree des operations de cache',
    ['operation']
)

# Utilisateurs
users_total = Gauge(
    'focus_api_users_total',
    'Nombre total d\'utilisateurs',
    ['status']  # active, inactive, verified
)

users_registered_total = Counter(
    'focus_api_users_registered_total',
    'Total des inscriptions d\'utilisateurs'
)

users_logged_in_total = Counter(
    'focus_api_users_logged_in_total',
    'Total des connexions utilisateurs'
)

# Activites
activities_created_total = Counter(
    'focus_api_activities_created_total',
    'Total des activites creees',
    ['app_name']
)

activities_duration_minutes = Histogram(
    'focus_api_activities_duration_minutes',
    'Duree des activites en minutes',
    ['app_name']
)

# Challenges
challenges_total = Gauge(
    'focus_api_challenges_total',
    'Nombre total de challenges',
    ['status']  # pending, active, completed
)

challenges_created_total = Counter(
    'focus_api_challenges_created_total',
    'Total des challenges crees'
)

challenges_participants_total = Gauge(
    'focus_api_challenges_participants_total',
    'Nombre total de participants aux challenges'
)

# Emails
emails_sent_total = Counter(
    'focus_api_emails_sent_total',
    'Total des emails envoyes',
    ['type', 'status']  # verification, reset, etc. / success, failed
)

# Blocages
apps_blocked_total = Counter(
    'focus_api_apps_blocked_total',
    'Total des applications bloquees',
    ['app_name']
)

limits_reached_total = Counter(
    'focus_api_limits_reached_total',
    'Total des limites atteintes',
    ['app_name']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour collecter automatiquement les metriques des requetes HTTP
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercepte chaque requete pour collecter les metriques

        Args:
            request: Requete HTTP
            call_next: Fonction suivante dans la chaine

        Returns:
            Response: Reponse HTTP
        """
        # Ignore l'endpoint de metriques lui-meme
        if request.url.path == settings.METRICS_ENDPOINT:
            return await call_next(request)

        # Extrait les informations de la requete
        method = request.method
        endpoint = request.url.path

        # Incremente le compteur de requetes en cours
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Demarre le chronometre
        start_time = time.time()

        try:
            # Execute la requete
            response = await call_next(request)

            # Calcule la duree
            duration = time.time() - start_time

            # Enregistre les metriques
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Enregistre les erreurs
            if response.status_code >= 400:
                error_type = "client_error" if response.status_code < 500 else "server_error"
                http_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    error_type=error_type
                ).inc()

            return response

        except Exception as e:
            # Enregistre l'erreur
            http_errors_total.labels(
                method=method,
                endpoint=endpoint,
                error_type=type(e).__name__
            ).inc()

            # Relance l'exception
            raise

        finally:
            # Decremente le compteur de requetes en cours
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def track_user_registration() -> None:
    """Enregistre une inscription utilisateur"""
    users_registered_total.inc()
    logger.debug("Metrique: Inscription utilisateur")


def track_user_login() -> None:
    """Enregistre une connexion utilisateur"""
    users_logged_in_total.inc()
    logger.debug("Metrique: Connexion utilisateur")


def track_activity_created(app_name: str, duration_minutes: float) -> None:
    """
    Enregistre la creation d'une activite

    Args:
        app_name: Nom de l'application
        duration_minutes: Duree en minutes
    """
    activities_created_total.labels(app_name=app_name).inc()
    activities_duration_minutes.labels(app_name=app_name).observe(duration_minutes)
    logger.debug(f"Metrique: Activite creee ({app_name}, {duration_minutes}min)")


def track_challenge_created() -> None:
    """Enregistre la creation d'un challenge"""
    challenges_created_total.inc()
    logger.debug("Metrique: Challenge cree")


def track_email_sent(email_type: str, success: bool) -> None:
    """
    Enregistre l'envoi d'un email

    Args:
        email_type: Type d'email (verification, reset, etc.)
        success: True si envoye avec succes
    """
    status = "success" if success else "failed"
    emails_sent_total.labels(type=email_type, status=status).inc()
    logger.debug(f"Metrique: Email {email_type} {status}")


def track_app_blocked(app_name: str) -> None:
    """
    Enregistre le blocage d'une application

    Args:
        app_name: Nom de l'application
    """
    apps_blocked_total.labels(app_name=app_name).inc()
    logger.debug(f"Metrique: App bloquee ({app_name})")


def track_limit_reached(app_name: str) -> None:
    """
    Enregistre qu'une limite a ete atteinte

    Args:
        app_name: Nom de l'application
    """
    limits_reached_total.labels(app_name=app_name).inc()
    logger.debug(f"Metrique: Limite atteinte ({app_name})")


def track_cache_hit() -> None:
    """Enregistre un hit de cache"""
    cache_hits_total.inc()


def track_cache_miss() -> None:
    """Enregistre un miss de cache"""
    cache_misses_total.inc()


def track_db_query(operation: str, duration: float) -> None:
    """
    Enregistre une requete en base de donnees

    Args:
        operation: Type d'operation (SELECT, INSERT, etc.)
        duration: Duree en secondes
    """
    db_queries_total.labels(operation=operation).inc()
    db_query_duration_seconds.labels(operation=operation).observe(duration)


def update_users_gauge(active: int, inactive: int, verified: int) -> None:
    """
    Met a jour le gauge des utilisateurs

    Args:
        active: Nombre d'utilisateurs actifs
        inactive: Nombre d'utilisateurs inactifs
        verified: Nombre d'utilisateurs verifies
    """
    users_total.labels(status="active").set(active)
    users_total.labels(status="inactive").set(inactive)
    users_total.labels(status="verified").set(verified)


def update_challenges_gauge(pending: int, active: int, completed: int) -> None:
    """
    Met a jour le gauge des challenges

    Args:
        pending: Nombre de challenges en attente
        active: Nombre de challenges actifs
        completed: Nombre de challenges termines
    """
    challenges_total.labels(status="pending").set(pending)
    challenges_total.labels(status="active").set(active)
    challenges_total.labels(status="completed").set(completed)


def get_metrics() -> bytes:
    """
    Genere les metriques au format Prometheus

    Returns:
        bytes: Metriques au format texte Prometheus
    """
    return generate_latest()


def get_metrics_content_type() -> str:
    """
    Retourne le content-type pour les metriques Prometheus

    Returns:
        str: Content-Type
    """
    return CONTENT_TYPE_LATEST
