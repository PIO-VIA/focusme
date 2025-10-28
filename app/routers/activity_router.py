"""
Router des activités
Gère le suivi du temps d'utilisation des applications
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models import Activity, User
from app.schemas.activity_schema import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityStats,
    DailyStats,
    WeeklyStats
)
from app.utils.jwt_handler import get_current_verified_user
from app.services.timer_service import (
    get_daily_stats,
    get_weekly_stats,
    get_app_stats,
    check_and_update_blocked_apps,
    calculate_app_usage_today
)
from app.services.log_service import log_limit_reached

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity: ActivityCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Enregistre une nouvelle activité (temps d'utilisation d'une app)
    """
    # Crée l'activité
    new_activity = Activity(
        user_id=current_user.id,
        app_name=activity.app_name,
        app_package=activity.app_package,
        app_category=activity.app_category,
        duration_minutes=activity.duration_minutes,
        start_time=activity.start_time,
        end_time=activity.end_time,
        activity_date=activity.activity_date or date.today(),
        device_type=activity.device_type,
        session_id=activity.session_id
    )

    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)

    # Vérifie les limites et met à jour les apps bloquées
    apps_to_block = check_and_update_blocked_apps(db, current_user.id)

    # Log si des limites ont été atteintes
    for blocked_app in apps_to_block:
        await log_limit_reached(
            db,
            current_user.id,
            blocked_app.app_name,
            blocked_app.current_usage_today
        )

    return new_activity


@router.get("/", response_model=List[ActivityResponse])
async def get_user_activities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    app_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les activités de l'utilisateur avec filtres et pagination
    """
    query = db.query(Activity).filter(Activity.user_id == current_user.id)

    # Filtres optionnels
    if app_name:
        query = query.filter(Activity.app_name.ilike(f"%{app_name}%"))
    if start_date:
        query = query.filter(Activity.activity_date >= start_date)
    if end_date:
        query = query.filter(Activity.activity_date <= end_date)

    # Pagination
    activities = query.order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()

    return activities


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère une activité spécifique par ID
    """
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activité non trouvée"
        )

    return activity


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    activity_update: ActivityUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour une activité
    """
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activité non trouvée"
        )

    # Met à jour les champs fournis
    update_data = activity_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)

    return activity


@router.delete("/{activity_id}")
async def delete_activity(
    activity_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Supprime une activité
    """
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activité non trouvée"
        )

    db.delete(activity)
    db.commit()

    return {"message": "Activité supprimée avec succès"}


@router.get("/stats/daily", response_model=DailyStats)
async def get_daily_statistics(
    target_date: Optional[date] = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques quotidiennes
    """
    stats = get_daily_stats(db, current_user.id, target_date)
    return stats


@router.get("/stats/weekly", response_model=WeeklyStats)
async def get_weekly_statistics(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques hebdomadaires
    """
    stats = get_weekly_stats(db, current_user.id)
    return stats


@router.get("/stats/app/{app_name}", response_model=ActivityStats)
async def get_app_statistics(
    app_name: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques pour une application spécifique
    """
    stats = get_app_stats(db, current_user.id, app_name)
    return stats


@router.get("/stats/today-usage/{app_name}")
async def get_today_app_usage(
    app_name: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère l'utilisation d'une app aujourd'hui
    """
    usage = calculate_app_usage_today(db, current_user.id, app_name)
    return {
        "app_name": app_name,
        "today_usage_minutes": usage,
        "today_usage_hours": round(usage / 60, 2)
    }
