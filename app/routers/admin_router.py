"""
Router administrateur
Gestion complète des utilisateurs, statistiques, logs et challenges
Accessible uniquement aux administrateurs
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta, date

from app.database import get_db
from app.models import User, Activity, Challenge, ChallengeParticipant, BlockedApp, Log
from app.models.user import UserRole
from app.models.challenge import ChallengeStatus
from app.models.log import LogAction
from app.schemas.user_schema import UserResponse, UserUpdate
from app.schemas.log_schema import LogResponse
from app.schemas.challenge_schema import ChallengeResponse
from app.utils.jwt_handler import get_current_admin_user
from app.services.log_service import log_user_deleted, log_user_deactivated

router = APIRouter(prefix="/admin", tags=["Admin"])


# ========================
# GESTION DES UTILISATEURS
# ========================

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0, description="Nombre d'utilisateurs à sauter"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'utilisateurs à récupérer"),
    role_filter: Optional[UserRole] = Query(None, description="Filtrer par rôle"),
    is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
    is_verified: Optional[bool] = Query(None, description="Filtrer par statut vérifié"),
    search: Optional[str] = Query(None, description="Rechercher par nom ou email"),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère tous les utilisateurs avec filtres

    - Pagination avec skip et limit
    - Filtrage par rôle, statut actif/vérifié
    - Recherche par nom d'utilisateur ou email
    """
    query = db.query(User)

    # Applique les filtres
    if role_filter:
        query = query.filter(User.role == role_filter)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.username.like(search_pattern)) |
            (User.email.like(search_pattern)) |
            (User.full_name.like(search_pattern))
        )

    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère un utilisateur spécifique par son ID
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour les informations d'un utilisateur

    - L'admin peut modifier tous les champs sauf le mot de passe
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    # Met à jour les champs fournis
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Désactive un compte utilisateur

    - L'utilisateur ne pourra plus se connecter
    - Les données sont conservées
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de désactiver un compte administrateur"
        )

    user.is_active = False
    db.commit()

    # Log la désactivation
    await log_user_deactivated(db, current_admin, user)

    return {"message": f"Utilisateur {user.username} désactivé avec succès"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Réactive un compte utilisateur
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    user.is_active = True
    db.commit()

    return {"message": f"Utilisateur {user.username} réactivé avec succès"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Supprime définitivement un utilisateur

    - Supprime toutes les données associées (cascade)
    - Action irréversible
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de supprimer un compte administrateur"
        )

    # Log la suppression avant de supprimer
    await log_user_deleted(db, current_admin, user)

    username = user.username
    db.delete(user)
    db.commit()

    return {"message": f"Utilisateur {username} supprimé définitivement"}


# ========================
# STATISTIQUES GLOBALES
# ========================

@router.get("/stats/overview")
async def get_overview_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques générales de l'application

    - Nombre total d'utilisateurs
    - Utilisateurs actifs/vérifiés
    - Nombre de challenges
    - Activités récentes
    """
    # Statistiques utilisateurs
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    verified_users = db.query(func.count(User.id)).filter(User.is_verified == True).scalar()

    # Nouveaux utilisateurs (derniers 7 jours)
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar()

    # Statistiques challenges
    total_challenges = db.query(func.count(Challenge.id)).scalar()
    active_challenges = db.query(func.count(Challenge.id)).filter(
        Challenge.status == ChallengeStatus.ACTIVE
    ).scalar()
    completed_challenges = db.query(func.count(Challenge.id)).filter(
        Challenge.status == ChallengeStatus.COMPLETED
    ).scalar()

    # Statistiques d'activité
    today = date.today()
    activities_today = db.query(func.count(Activity.id)).filter(
        Activity.activity_date == today
    ).scalar()

    total_activity_time = db.query(func.sum(Activity.duration_minutes)).scalar() or 0

    # Utilisateurs les plus actifs (par temps d'utilisation)
    top_users = db.query(
        User.username,
        User.email,
        func.sum(Activity.duration_minutes).label('total_minutes')
    ).join(Activity, User.id == Activity.user_id).group_by(
        User.id, User.username, User.email
    ).order_by(desc('total_minutes')).limit(5).all()

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
            "new_this_week": new_users_week
        },
        "challenges": {
            "total": total_challenges,
            "active": active_challenges,
            "completed": completed_challenges
        },
        "activities": {
            "today": activities_today,
            "total_time_minutes": float(total_activity_time)
        },
        "top_users": [
            {
                "username": user.username,
                "email": user.email,
                "total_minutes": float(total_minutes)
            }
            for user, total_minutes in top_users
        ]
    }


@router.get("/stats/users-growth")
async def get_users_growth(
    days: int = Query(30, ge=1, le=365, description="Nombre de jours à analyser"),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques de croissance des utilisateurs

    - Nombre d'inscriptions par jour
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    users_by_day = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).order_by('date').all()

    return {
        "period_days": days,
        "start_date": start_date.date(),
        "end_date": datetime.utcnow().date(),
        "daily_signups": [
            {
                "date": str(day),
                "count": count
            }
            for day, count in users_by_day
        ]
    }


@router.get("/stats/app-usage")
async def get_app_usage_stats(
    days: int = Query(7, ge=1, le=90, description="Nombre de jours à analyser"),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques d'utilisation des applications

    - Top des applications les plus utilisées
    - Temps total par application
    """
    start_date = date.today() - timedelta(days=days)

    app_stats = db.query(
        Activity.app_name,
        func.sum(Activity.duration_minutes).label('total_minutes'),
        func.count(Activity.id).label('activity_count'),
        func.count(func.distinct(Activity.user_id)).label('unique_users')
    ).filter(
        Activity.activity_date >= start_date
    ).group_by(
        Activity.app_name
    ).order_by(desc('total_minutes')).limit(20).all()

    return {
        "period_days": days,
        "start_date": str(start_date),
        "end_date": str(date.today()),
        "top_apps": [
            {
                "app_name": app_name,
                "total_minutes": float(total_minutes),
                "activity_count": activity_count,
                "unique_users": unique_users
            }
            for app_name, total_minutes, activity_count, unique_users in app_stats
        ]
    }


# ========================
# GESTION DES CHALLENGES
# ========================

@router.get("/challenges", response_model=List[ChallengeResponse])
async def get_all_challenges(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[ChallengeStatus] = Query(None),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère tous les challenges (publics et privés)
    """
    query = db.query(Challenge)

    if status_filter:
        query = query.filter(Challenge.status == status_filter)

    challenges = query.order_by(desc(Challenge.created_at)).offset(skip).limit(limit).all()
    return challenges


@router.delete("/challenges/{challenge_id}")
async def delete_challenge_admin(
    challenge_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Supprime un challenge (admin peut supprimer n'importe quel challenge)
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge non trouvé"
        )

    db.delete(challenge)
    db.commit()

    return {"message": "Challenge supprimé avec succès"}


# ========================
# LOGS ET AUDIT
# ========================

@router.get("/logs", response_model=List[LogResponse])
async def get_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    action_filter: Optional[LogAction] = Query(None, description="Filtrer par type d'action"),
    user_id: Optional[int] = Query(None, description="Filtrer par utilisateur"),
    days: int = Query(7, ge=1, le=90, description="Nombre de jours à récupérer"),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les logs d'activité de l'application

    - Affiche toutes les actions importantes
    - Filtrage par type d'action et utilisateur
    - Pagination
    """
    query = db.query(Log)

    # Filtre par période
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(Log.timestamp >= start_date)

    # Applique les filtres
    if action_filter:
        query = query.filter(Log.action == action_filter)

    if user_id:
        query = query.filter(Log.user_id == user_id)

    logs = query.order_by(desc(Log.timestamp)).offset(skip).limit(limit).all()
    return logs


@router.get("/logs/stats")
async def get_log_stats(
    days: int = Query(7, ge=1, le=90),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques des logs

    - Nombre d'actions par type
    - Actions les plus fréquentes
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    action_stats = db.query(
        Log.action,
        func.count(Log.id).label('count')
    ).filter(
        Log.timestamp >= start_date
    ).group_by(
        Log.action
    ).order_by(desc('count')).all()

    return {
        "period_days": days,
        "start_date": str(start_date.date()),
        "end_date": str(datetime.utcnow().date()),
        "actions": [
            {
                "action": action,
                "count": count
            }
            for action, count in action_stats
        ]
    }


@router.delete("/logs/cleanup")
async def cleanup_old_logs(
    days: int = Query(90, ge=30, description="Supprimer les logs plus vieux que X jours"),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Supprime les logs anciens pour libérer de l'espace

    - Minimum 30 jours de rétention
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    deleted_count = db.query(Log).filter(Log.timestamp < cutoff_date).delete()
    db.commit()

    return {
        "message": f"{deleted_count} logs supprimés",
        "cutoff_date": str(cutoff_date.date())
    }


# ========================
# SYSTÈME
# ========================

@router.get("/system/health")
async def system_health(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Vérifie la santé du système

    - État de la base de données
    - Statistiques système
    """
    try:
        # Test de connexion à la DB
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Compte des tables principales
    tables_count = {
        "users": db.query(func.count(User.id)).scalar(),
        "activities": db.query(func.count(Activity.id)).scalar(),
        "challenges": db.query(func.count(Challenge.id)).scalar(),
        "logs": db.query(func.count(Log.id)).scalar()
    }

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow(),
        "tables": tables_count
    }
