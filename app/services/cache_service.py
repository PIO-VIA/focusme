"""
Service de cache avec Redis
Gere la mise en cache des donnees pour ameliorer les performances
"""
import json
import logging
from typing import Optional, Any, Union
from datetime import timedelta
import redis.asyncio as redis
from functools import wraps

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service de gestion du cache Redis
    Fournit des methodes pour stocker et recuperer des donnees en cache
    """

    def __init__(self):
        """Initialise la connexion Redis"""
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.CACHE_ENABLED

    async def connect(self) -> None:
        """
        Etablit la connexion a Redis
        """
        if not self.enabled:
            logger.info("Cache Redis desactive")
            return

        try:
            # Utilise REDIS_URL si disponible, sinon construit l'URL
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            else:
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    encoding="utf-8",
                    decode_responses=True
                )

            # Test de connexion
            await self.redis_client.ping()
            logger.info(f"Connexion Redis etablie: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

        except Exception as e:
            logger.error(f"Impossible de se connecter a Redis: {e}")
            self.enabled = False
            self.redis_client = None

    async def disconnect(self) -> None:
        """
        Ferme la connexion Redis
        """
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Connexion Redis fermee")

    async def get(self, key: str) -> Optional[Any]:
        """
        Recupere une valeur depuis le cache

        Args:
            key: Cle du cache

        Returns:
            Optional[Any]: Valeur en cache ou None
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None

        except Exception as e:
            logger.error(f"Erreur lors de la lecture du cache {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Stocke une valeur dans le cache

        Args:
            key: Cle du cache
            value: Valeur a stocker
            ttl: Duree de vie en secondes (defaut: settings.CACHE_TTL)

        Returns:
            bool: True si reussi, False sinon
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            ttl = ttl or settings.CACHE_TTL
            serialized_value = json.dumps(value, default=str)

            await self.redis_client.setex(
                key,
                ttl,
                serialized_value
            )
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'ecriture du cache {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Supprime une cle du cache

        Args:
            key: Cle a supprimer

        Returns:
            bool: True si reussi, False sinon
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            result = await self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return bool(result)

        except Exception as e:
            logger.error(f"Erreur lors de la suppression du cache {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Supprime toutes les cles correspondant a un pattern

        Args:
            pattern: Pattern Redis (ex: "user:*")

        Returns:
            int: Nombre de cles supprimees
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cache DELETE PATTERN: {pattern} ({deleted} cles)")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Erreur lors de la suppression du pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Verifie si une cle existe dans le cache

        Args:
            key: Cle a verifier

        Returns:
            bool: True si la cle existe
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            result = await self.redis_client.exists(key)
            return bool(result)

        except Exception as e:
            logger.error(f"Erreur lors de la verification de {key}: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        Vide tout le cache

        Returns:
            bool: True si reussi
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            await self.redis_client.flushdb()
            logger.warning("Cache Redis entierement vide")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du vidage du cache: {e}")
            return False

    async def get_info(self) -> dict:
        """
        Recupere les informations sur Redis

        Returns:
            dict: Informations Redis
        """
        if not self.enabled or not self.redis_client:
            return {"enabled": False, "status": "disabled"}

        try:
            info = await self.redis_client.info()
            return {
                "enabled": True,
                "status": "connected",
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": await self.redis_client.dbsize()
            }

        except Exception as e:
            logger.error(f"Erreur lors de la recuperation des infos Redis: {e}")
            return {"enabled": True, "status": "error", "error": str(e)}


# Instance globale du service de cache
cache_service = CacheService()


def cache_key(*args, **kwargs) -> str:
    """
    Genere une cle de cache a partir des arguments

    Args:
        *args: Arguments positionnels
        **kwargs: Arguments nommes

    Returns:
        str: Cle de cache unique
    """
    parts = [str(arg) for arg in args]
    parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    return ":".join(parts)


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorateur pour mettre en cache le resultat d'une fonction

    Args:
        ttl: Duree de vie du cache en secondes
        key_prefix: Prefixe pour la cle de cache

    Usage:
        @cached(ttl=300, key_prefix="user")
        async def get_user(user_id: int):
            return db.query(User).filter(User.id == user_id).first()
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Genere la cle de cache
            cache_key_str = cache_key(
                key_prefix or func.__name__,
                *args,
                **kwargs
            )

            # Essaie de recuperer depuis le cache
            cached_value = await cache_service.get(cache_key_str)
            if cached_value is not None:
                return cached_value

            # Execute la fonction
            result = await func(*args, **kwargs)

            # Stocke le resultat en cache
            await cache_service.set(cache_key_str, result, ttl)

            return result

        return wrapper
    return decorator


async def invalidate_user_cache(user_id: int) -> None:
    """
    Invalide tout le cache lie a un utilisateur

    Args:
        user_id: ID de l'utilisateur
    """
    pattern = f"*user*{user_id}*"
    await cache_service.delete_pattern(pattern)
    logger.info(f"Cache invalide pour l'utilisateur {user_id}")


async def invalidate_challenge_cache(challenge_id: int) -> None:
    """
    Invalide tout le cache lie a un challenge

    Args:
        challenge_id: ID du challenge
    """
    pattern = f"*challenge*{challenge_id}*"
    await cache_service.delete_pattern(pattern)
    logger.info(f"Cache invalide pour le challenge {challenge_id}")
