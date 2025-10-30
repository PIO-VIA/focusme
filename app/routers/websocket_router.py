"""
Router WebSocket
Gere les connexions WebSocket pour les notifications en temps reel
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
import asyncio

from app.database import get_db
from app.services.websocket_service import manager, heartbeat_task
from app.utils.jwt_handler import decode_token
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def get_current_user_ws(
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
) -> User:
    """
    Authentifie l'utilisateur via token JWT pour WebSocket

    Args:
        token: Token JWT
        db: Session de base de donnees

    Returns:
        User: Utilisateur authentifie

    Raises:
        Exception: Si token invalide
    """
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise Exception("Token invalide")

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise Exception("Utilisateur non trouve ou inactif")

        return user

    except Exception as e:
        logger.error(f"Erreur authentification WebSocket: {e}")
        raise


@router.websocket("/notifications")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint WebSocket pour les notifications en temps reel

    Le client doit se connecter avec un token JWT valide

    Usage:
        ws://localhost:8000/api/ws/notifications?token=<jwt_token>

    Messages recus:
        - type: "connection" - Confirmation de connexion
        - type: "heartbeat" - Ping periodique
        - type: "notification" - Notification utilisateur
        - type: "error" - Erreur

    Le client peut envoyer:
        - {"action": "ping"} - Pour tester la connexion
        - {"action": "subscribe", "events": [...]} - S'abonner a des evenements
    """
    user = None

    try:
        # Authentifie l'utilisateur
        user = await get_current_user_ws(token=token, db=db)

        # Connecte l'utilisateur
        await manager.connect(websocket, user.id)

        # Lance la tache de heartbeat
        heartbeat = asyncio.create_task(heartbeat_task(websocket))

        try:
            # Boucle de reception des messages
            while True:
                # Attends un message du client
                data = await websocket.receive_json()

                # Traite les actions du client
                action = data.get("action")

                if action == "ping":
                    # Repond au ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": data.get("timestamp")
                    })

                elif action == "subscribe":
                    # Abonnement a des evenements specifiques
                    events = data.get("events", [])
                    logger.info(f"Utilisateur {user.id} abonne aux evenements: {events}")

                    await websocket.send_json({
                        "type": "subscribed",
                        "events": events,
                        "message": "Abonnement reussi"
                    })

                elif action == "unsubscribe":
                    # Desabonnement
                    events = data.get("events", [])
                    logger.info(f"Utilisateur {user.id} desabonne des evenements: {events}")

                    await websocket.send_json({
                        "type": "unsubscribed",
                        "events": events,
                        "message": "Desabonnement reussi"
                    })

                elif action == "get_stats":
                    # Statistiques de connexion
                    stats = manager.get_stats()
                    await websocket.send_json({
                        "type": "stats",
                        "data": stats
                    })

                else:
                    # Action inconnue
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Action inconnue: {action}"
                    })

        except WebSocketDisconnect:
            # Client deconnecte normalement
            heartbeat.cancel()
            if user:
                manager.disconnect(websocket, user.id)
            logger.info(f"Utilisateur {user.id if user else 'inconnu'} deconnecte")

    except Exception as e:
        # Erreur d'authentification ou autre
        logger.error(f"Erreur WebSocket: {e}")

        try:
            await websocket.send_json({
                "type": "error",
                "message": "Erreur d'authentification ou de connexion"
            })
            await websocket.close()
        except:
            pass

        if user:
            manager.disconnect(websocket, user.id)


@router.get("/stats")
async def get_websocket_stats():
    """
    Retourne les statistiques des connexions WebSocket

    Returns:
        dict: Statistiques
    """
    stats = manager.get_stats()

    return {
        "websocket_enabled": True,
        "active_users": stats["total_users"],
        "active_connections": stats["total_connections"],
        "connected_user_ids": list(manager.get_connected_users())
    }
