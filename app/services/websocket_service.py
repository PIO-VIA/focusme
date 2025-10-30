"""
Service de notifications WebSocket
Gere les connexions WebSocket et l'envoi de notifications en temps reel
"""
import logging
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestionnaire de connexions WebSocket
    Gere plusieurs connexions simultanees et l'envoi de messages
    """

    def __init__(self):
        """Initialise le gestionnaire de connexions"""
        # Dictionnaire: user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.connection_times: Dict[WebSocket, datetime] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Accepte une nouvelle connexion WebSocket

        Args:
            websocket: Connexion WebSocket
            user_id: ID de l'utilisateur
        """
        await websocket.accept()

        # Ajoute la connexion au gestionnaire
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.connection_times[websocket] = datetime.utcnow()

        logger.info(f"Utilisateur {user_id} connecte via WebSocket")
        logger.debug(f"Connexions actives: {self.get_stats()}")

        # Envoie un message de bienvenue
        await self.send_personal_message(
            {
                "type": "connection",
                "message": "Connexion etablie avec succes",
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Deconnecte un WebSocket

        Args:
            websocket: Connexion a deconnecter
            user_id: ID de l'utilisateur
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Supprime l'entree si plus aucune connexion
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        if websocket in self.connection_times:
            connection_duration = (datetime.utcnow() - self.connection_times[websocket]).total_seconds()
            del self.connection_times[websocket]
            logger.info(f"Utilisateur {user_id} deconnecte apres {connection_duration:.0f}s")

        logger.debug(f"Connexions actives: {self.get_stats()}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """
        Envoie un message a une connexion specifique

        Args:
            message: Message a envoyer (dict)
            websocket: Connexion cible
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message: {e}")

    async def send_to_user(self, message: Dict[str, Any], user_id: int) -> int:
        """
        Envoie un message a toutes les connexions d'un utilisateur

        Args:
            message: Message a envoyer
            user_id: ID de l'utilisateur cible

        Returns:
            int: Nombre de connexions atteintes
        """
        if user_id not in self.active_connections:
            logger.debug(f"Utilisateur {user_id} n'a pas de connexion active")
            return 0

        connections = self.active_connections[user_id].copy()
        sent_count = 0

        for connection in connections:
            try:
                await self.send_personal_message(message, connection)
                sent_count += 1
            except Exception as e:
                logger.error(f"Erreur envoi a utilisateur {user_id}: {e}")
                # Deconnecte les connexions mortes
                self.disconnect(connection, user_id)

        logger.debug(f"Message envoye a {sent_count} connexion(s) de l'utilisateur {user_id}")
        return sent_count

    async def broadcast(self, message: Dict[str, Any], exclude_user: Optional[int] = None) -> int:
        """
        Diffuse un message a tous les utilisateurs connectes

        Args:
            message: Message a diffuser
            exclude_user: ID utilisateur a exclure (optionnel)

        Returns:
            int: Nombre total de connexions atteintes
        """
        sent_count = 0

        for user_id, connections in list(self.active_connections.items()):
            if exclude_user and user_id == exclude_user:
                continue

            for connection in connections.copy():
                try:
                    await self.send_personal_message(message, connection)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Erreur broadcast a utilisateur {user_id}: {e}")
                    self.disconnect(connection, user_id)

        logger.info(f"Broadcast envoye a {sent_count} connexion(s)")
        return sent_count

    def is_user_connected(self, user_id: int) -> bool:
        """
        Verifie si un utilisateur a au moins une connexion active

        Args:
            user_id: ID de l'utilisateur

        Returns:
            bool: True si connecte
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_connected_users(self) -> Set[int]:
        """
        Retourne l'ensemble des IDs utilisateurs connectes

        Returns:
            Set[int]: IDs des utilisateurs
        """
        return set(self.active_connections.keys())

    def get_stats(self) -> Dict[str, int]:
        """
        Retourne des statistiques sur les connexions

        Returns:
            Dict: Statistiques
        """
        total_connections = sum(len(conns) for conns in self.active_connections.values())

        return {
            "total_users": len(self.active_connections),
            "total_connections": total_connections
        }


# Instance globale du gestionnaire de connexions
manager = ConnectionManager()


class NotificationService:
    """Service pour envoyer differents types de notifications"""

    @staticmethod
    async def notify_user(
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envoie une notification a un utilisateur

        Args:
            user_id: ID de l'utilisateur
            notification_type: Type de notification (info, warning, error, success)
            title: Titre de la notification
            message: Message de la notification
            data: Donnees additionnelles (optionnel)

        Returns:
            bool: True si envoyee
        """
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        sent = await manager.send_to_user(notification, user_id)
        return sent > 0

    @staticmethod
    async def notify_activity_update(user_id: int, activity_data: Dict[str, Any]) -> bool:
        """
        Notifie l'utilisateur d'une nouvelle activite

        Args:
            user_id: ID de l'utilisateur
            activity_data: Donnees de l'activite

        Returns:
            bool: True si envoyee
        """
        return await NotificationService.notify_user(
            user_id=user_id,
            notification_type="info",
            title="Nouvelle activite enregistree",
            message=f"Activite sur {activity_data.get('app_name')} enregistree",
            data=activity_data
        )

    @staticmethod
    async def notify_limit_warning(user_id: int, app_name: str, percentage: float) -> bool:
        """
        Notifie que l'utilisateur approche de sa limite

        Args:
            user_id: ID de l'utilisateur
            app_name: Nom de l'application
            percentage: Pourcentage utilise

        Returns:
            bool: True si envoyee
        """
        return await NotificationService.notify_user(
            user_id=user_id,
            notification_type="warning",
            title="Limite bientot atteinte",
            message=f"Vous avez utilise {percentage:.0f}% de votre limite pour {app_name}",
            data={"app_name": app_name, "percentage": percentage}
        )

    @staticmethod
    async def notify_app_blocked(user_id: int, app_name: str) -> bool:
        """
        Notifie que l'application est bloquee

        Args:
            user_id: ID de l'utilisateur
            app_name: Nom de l'application

        Returns:
            bool: True si envoyee
        """
        return await NotificationService.notify_user(
            user_id=user_id,
            notification_type="error",
            title="Application bloquee",
            message=f"{app_name} est maintenant bloquee - limite atteinte",
            data={"app_name": app_name}
        )

    @staticmethod
    async def notify_challenge_update(
        user_id: int,
        challenge_title: str,
        update_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Notifie d'une mise a jour de challenge

        Args:
            user_id: ID de l'utilisateur
            challenge_title: Titre du challenge
            update_type: Type de mise a jour (joined, started, completed, etc.)
            message: Message de la notification
            data: Donnees additionnelles

        Returns:
            bool: True si envoyee
        """
        return await NotificationService.notify_user(
            user_id=user_id,
            notification_type="success",
            title=f"Challenge: {challenge_title}",
            message=message,
            data={"update_type": update_type, **(data or {})}
        )

    @staticmethod
    async def notify_leaderboard_update(
        user_ids: list[int],
        challenge_title: str,
        leaderboard_data: Dict[str, Any]
    ) -> int:
        """
        Notifie plusieurs utilisateurs d'une mise a jour du leaderboard

        Args:
            user_ids: Liste des IDs utilisateurs
            challenge_title: Titre du challenge
            leaderboard_data: Donnees du classement

        Returns:
            int: Nombre d'utilisateurs notifies
        """
        count = 0
        for user_id in user_ids:
            sent = await NotificationService.notify_user(
                user_id=user_id,
                notification_type="info",
                title=f"Classement mis a jour: {challenge_title}",
                message="Consultez le nouveau classement",
                data=leaderboard_data
            )
            if sent:
                count += 1

        return count


# Instance globale du service de notifications
notification_service = NotificationService()


async def heartbeat_task(websocket: WebSocket):
    """
    Tache de heartbeat pour maintenir la connexion active

    Args:
        websocket: Connexion WebSocket
    """
    try:
        while True:
            await asyncio.sleep(settings.WEBSOCKET_HEARTBEAT_INTERVAL)
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Erreur heartbeat: {e}")
