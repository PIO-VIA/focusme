"""
Application principale FastAPI - Focus Backend
Point d'entree de l'API REST pour l'application Focus
"""
from fastapi import FastAPI, Request, status, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import logging.config
from datetime import datetime

from app.config import settings, LOGGING_CONFIG
from app.database import init_db, create_admin_user, check_db_connection
from app.services.cache_service import cache_service
from app.services.metrics_service import (
    PrometheusMiddleware,
    get_metrics,
    get_metrics_content_type
)
from app.routers import (
    auth_router,
    user_router,
    activity_router,
    challenge_router,
    blocked_router,
    admin_router,
    websocket_router
)

# Configuration du logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application
    Execute au demarrage et a l'arret
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Demarrage de {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)

    # Verifie la connexion a la base de donnees
    if not check_db_connection():
        logger.error("Impossible de se connecter a la base de donnees")
        raise Exception("Erreur de connexion a la base de donnees")

    # Initialise la base de donnees
    try:
        init_db()
        logger.info("Base de donnees initialisee avec succes")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de donnees: {e}")
        raise

    # Cree l'administrateur par defaut
    try:
        await create_admin_user()
    except Exception as e:
        logger.error(f"Erreur lors de la creation de l'admin: {e}")

    # Connecte le cache Redis
    try:
        await cache_service.connect()
        if cache_service.enabled:
            logger.info("Cache Redis connecte et operationnel")
    except Exception as e:
        logger.warning(f"Cache Redis non disponible: {e}")

    logger.info(f"API disponible sur: {settings.API_PREFIX}")
    logger.info(f"Documentation Swagger: {settings.API_PREFIX}/docs")
    logger.info(f"Metriques Prometheus: {settings.METRICS_ENDPOINT}")
    logger.info(f"Mode debug: {settings.DEBUG}")
    logger.info("Application prete a recevoir des requetes")

    yield

    # Shutdown
    logger.info("Arret de l'application...")
    logger.info("Nettoyage des ressources...")

    # Deconnecte Redis
    try:
        await cache_service.disconnect()
    except Exception as e:
        logger.error(f"Erreur lors de la deconnexion Redis: {e}")

    logger.info("Application arretee proprement")


# Creation de l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    API REST complete pour Focus - L'application de gestion du temps sur les reseaux sociaux

    ## Fonctionnalites principales

    * **Authentification** - Inscription, connexion, verification d'email, reinitialisation de mot de passe
    * **Gestion des utilisateurs** - Profils, parametres, statistiques personnelles
    * **Suivi des activites** - Enregistrement du temps passe sur les applications
    * **Blocage d'applications** - Gestion des limites et blocages automatiques
    * **Challenges** - Defis entre amis avec classements et recompenses
    * **Administration** - Tableau de bord complet pour les administrateurs

    ## Securite

    * Authentification JWT (Bearer Token)
    * Mots de passe haches avec bcrypt
    * Verification d'email obligatoire
    * Roles utilisateurs (user/admin)
    """,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan
)


# ========================
# MIDDLEWARE
# ========================

# Prometheus metrics (doit etre le premier middleware)
if settings.METRICS_ENABLED:
    app.add_middleware(PrometheusMiddleware)
    logger.info("Middleware Prometheus active")

# CORS - Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Middleware de logging des requetes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log toutes les requetes HTTP
    """
    start_time = datetime.utcnow()

    # Log la requete entrante
    logger.info(f"-> {request.method} {request.url.path}")

    try:
        response = await call_next(request)

        # Calcule le temps de traitement
        process_time = (datetime.utcnow() - start_time).total_seconds()

        # Log la reponse
        logger.info(
            f"OK {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        # Ajoute le temps de traitement dans les headers
        response.headers["X-Process-Time"] = str(process_time)

        return response

    except Exception as e:
        logger.error(f"ERROR {request.method} {request.url.path} - Error: {str(e)}")
        raise


# Middleware de securite - Trusted Hosts
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.focusapp.com"]
    )


# ========================
# GESTIONNAIRES D'ERREURS
# ========================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Gere les erreurs de validation des requetes
    """
    logger.warning(f"Erreur de validation: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Erreur de validation",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Gere toutes les erreurs non capturees
    """
    logger.error(f"Erreur non geree: {str(exc)}", exc_info=True)

    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Erreur interne du serveur",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erreur interne du serveur"}
        )


# ========================
# ROUTES PRINCIPALES
# ========================

@app.get("/", tags=["Root"])
async def root():
    """
    Route racine - Informations sur l'API
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "timestamp": datetime.utcnow(),
        "docs": f"{settings.API_PREFIX}/docs",
        "endpoints": {
            "auth": f"{settings.API_PREFIX}/auth",
            "users": f"{settings.API_PREFIX}/users",
            "activities": f"{settings.API_PREFIX}/activities",
            "challenges": f"{settings.API_PREFIX}/challenges",
            "blocked": f"{settings.API_PREFIX}/blocked",
            "admin": f"{settings.API_PREFIX}/admin"
        }
    }


@app.get(f"{settings.API_PREFIX}/health", tags=["Health"])
async def health_check():
    """
    Endpoint de sante pour les monitoring et load balancers
    """
    db_healthy = check_db_connection()

    # Verifie le statut du cache Redis
    cache_info = await cache_service.get_info()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "cache": cache_info,
        "timestamp": datetime.utcnow(),
        "version": settings.APP_VERSION
    }


@app.get(settings.METRICS_ENDPOINT, tags=["Monitoring"])
async def metrics():
    """
    Endpoint Prometheus - Expose les metriques de l'application

    Returns:
        Response: Metriques au format Prometheus
    """
    if not settings.METRICS_ENABLED:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Metriques desactivees"}
        )

    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type=get_metrics_content_type())


# ========================
# ENREGISTREMENT DES ROUTERS
# ========================

# Authentification
app.include_router(
    auth_router.router,
    prefix=settings.API_PREFIX
)

# Utilisateurs
app.include_router(
    user_router.router,
    prefix=settings.API_PREFIX
)

# Activites
app.include_router(
    activity_router.router,
    prefix=settings.API_PREFIX
)

# Challenges
app.include_router(
    challenge_router.router,
    prefix=settings.API_PREFIX
)

# Applications bloquees
app.include_router(
    blocked_router.router,
    prefix=settings.API_PREFIX
)

# Administration
app.include_router(
    admin_router.router,
    prefix=settings.API_PREFIX
)

# WebSocket (notifications en temps reel)
if settings.WEBSOCKET_ENABLED:
    app.include_router(
        websocket_router.router,
        prefix=settings.API_PREFIX
    )
    logger.info("WebSocket notifications activees")


# ========================
# POINT D'ENTREE
# ========================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True
    )
