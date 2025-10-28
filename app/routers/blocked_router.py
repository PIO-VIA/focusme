"""
Router des applications bloquées
Gère les limites et le blocage des applications
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import BlockedApp, User
from app.schemas.blocked_schema import (
    BlockedAppCreate,
    BlockedAppUpdate,
    BlockedAppResponse,
    BlockedAppStatus,
    BlockStatusUpdate,
    BlockedAppsListResponse
)
from app.utils.jwt_handler import get_current_verified_user
from app.services.timer_service import calculate_app_usage_today, get_time_until_unblock
from app.services.log_service import log_app_blocked
from datetime import datetime

router = APIRouter(prefix="/blocked-apps", tags=["Blocked Apps"])


@router.post("/", response_model=BlockedAppResponse, status_code=status.HTTP_201_CREATED)
async def create_blocked_app(
    blocked_app: BlockedAppCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Ajoute une application à surveiller/bloquer
    """
    # Vérifie si l'app existe déjà pour cet utilisateur
    existing = db.query(BlockedApp).filter(
        BlockedApp.user_id == current_user.id,
        BlockedApp.app_name == blocked_app.app_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette application est déjà dans votre liste"
        )

    # Crée l'app bloquée
    new_blocked_app = BlockedApp(
        user_id=current_user.id,
        app_name=blocked_app.app_name,
        app_package=blocked_app.app_package,
        app_category=blocked_app.app_category,
        daily_limit_minutes=blocked_app.daily_limit_minutes,
        block_start_time=blocked_app.block_start_time,
        block_end_time=blocked_app.block_end_time,
        block_on_weekends=blocked_app.block_on_weekends,
        notify_at_percentage=blocked_app.notify_at_percentage,
        is_blocked=False,
        current_usage_today=0
    )

    db.add(new_blocked_app)
    db.commit()
    db.refresh(new_blocked_app)

    # Calcule l'utilisation actuelle
    current_usage = calculate_app_usage_today(db, current_user.id, blocked_app.app_name)
    new_blocked_app.current_usage_today = int(current_usage)

    # Vérifie si l'app doit être bloquée immédiatement
    if current_usage >= blocked_app.daily_limit_minutes:
        new_blocked_app.is_blocked = True
        new_blocked_app.last_blocked_at = datetime.utcnow()

    db.commit()
    db.refresh(new_blocked_app)

    return new_blocked_app


@router.get("/", response_model=BlockedAppsListResponse)
async def get_blocked_apps(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère toutes les applications bloquées de l'utilisateur
    """
    blocked_apps = db.query(BlockedApp).filter(
        BlockedApp.user_id == current_user.id
    ).all()

    # Ajoute les propriétés calculées
    for app in blocked_apps:
        app.usage_percentage = app.usage_percentage
        app.remaining_minutes = app.remaining_minutes

    total_blocked = sum(1 for app in blocked_apps if app.is_blocked)
    total_active = len(blocked_apps) - total_blocked

    return BlockedAppsListResponse(
        blocked_apps=blocked_apps,
        total=len(blocked_apps),
        total_blocked=total_blocked,
        total_active=total_active
    )


@router.get("/{blocked_app_id}", response_model=BlockedAppResponse)
async def get_blocked_app(
    blocked_app_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère une application bloquée par ID
    """
    blocked_app = db.query(BlockedApp).filter(
        BlockedApp.id == blocked_app_id,
        BlockedApp.user_id == current_user.id
    ).first()

    if not blocked_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application bloquée non trouvée"
        )

    blocked_app.usage_percentage = blocked_app.usage_percentage
    blocked_app.remaining_minutes = blocked_app.remaining_minutes

    return blocked_app


@router.put("/{blocked_app_id}", response_model=BlockedAppResponse)
async def update_blocked_app(
    blocked_app_id: int,
    update_data: BlockedAppUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour les paramètres d'une application bloquée
    """
    blocked_app = db.query(BlockedApp).filter(
        BlockedApp.id == blocked_app_id,
        BlockedApp.user_id == current_user.id
    ).first()

    if not blocked_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application bloquée non trouvée"
        )

    # Met à jour les champs fournis
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(blocked_app, field, value)

    db.commit()
    db.refresh(blocked_app)

    return blocked_app


@router.delete("/{blocked_app_id}")
async def delete_blocked_app(
    blocked_app_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Supprime une application de la liste de blocage
    """
    blocked_app = db.query(BlockedApp).filter(
        BlockedApp.id == blocked_app_id,
        BlockedApp.user_id == current_user.id
    ).first()

    if not blocked_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application bloquée non trouvée"
        )

    db.delete(blocked_app)
    db.commit()

    return {"message": "Application retirée de la liste de blocage"}


@router.get("/status/{app_name}", response_model=BlockedAppStatus)
async def get_app_block_status(
    app_name: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Vérifie le statut de blocage d'une application
    """
    blocked_app = db.query(BlockedApp).filter(
        BlockedApp.user_id == current_user.id,
        BlockedApp.app_name == app_name
    ).first()

    if not blocked_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application non trouvée dans la liste de blocage"
        )

    # Met à jour l'utilisation actuelle
    current_usage = calculate_app_usage_today(db, current_user.id, app_name)
    blocked_app.current_usage_today = int(current_usage)
    db.commit()

    should_notify = (
        blocked_app.usage_percentage >= blocked_app.notify_at_percentage
        and not blocked_app.notification_sent
    )

    return BlockedAppStatus(
        app_name=blocked_app.app_name,
        is_blocked=blocked_app.is_blocked,
        usage_percentage=blocked_app.usage_percentage,
        remaining_minutes=blocked_app.remaining_minutes,
        should_notify=should_notify
    )


@router.post("/update-usage", response_model=dict)
async def update_app_usage(
    usage_update: BlockStatusUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour l'utilisation actuelle d'une application
    (appelé par le client pour mettre à jour le compteur)
    """
    blocked_app = db.query(BlockedApp).filter(
        BlockedApp.user_id == current_user.id,
        BlockedApp.app_name == usage_update.app_name
    ).first()

    if not blocked_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application non trouvée dans la liste de blocage"
        )

    # Ajoute le temps d'utilisation
    blocked_app.current_usage_today += usage_update.additional_minutes

    # Vérifie si l'app doit être bloquée
    if blocked_app.current_usage_today >= blocked_app.daily_limit_minutes:
        if not blocked_app.is_blocked:
            blocked_app.is_blocked = True
            blocked_app.last_blocked_at = datetime.utcnow()

            # Log le blocage
            await log_app_blocked(db, current_user.id, blocked_app.app_name, blocked_app.id)

    db.commit()

    time_until_unblock = get_time_until_unblock(blocked_app)

    return {
        "is_blocked": blocked_app.is_blocked,
        "current_usage_minutes": blocked_app.current_usage_today,
        "remaining_minutes": blocked_app.remaining_minutes,
        "time_until_unblock_seconds": time_until_unblock
    }
