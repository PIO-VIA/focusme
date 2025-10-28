"""
Router des utilisateurs
Gère le profil, les paramètres et les informations utilisateur
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User
from app.schemas.user_schema import UserResponse, UserUpdate, PasswordChange, UserPublic
from app.schemas.activity_schema import ActivitySummary
from app.utils.jwt_handler import get_current_user, get_current_verified_user
from app.utils.security import verify_password, get_password_hash
from app.services.timer_service import get_daily_stats, get_weekly_stats, calculate_progress_vs_limit

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Récupère le profil de l'utilisateur connecté
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour le profil de l'utilisateur connecté
    """
    # Met à jour les champs fournis
    update_data = user_update.model_dump(exclude_unset=True)

    # Vérifie si le nouveau username est déjà pris
    if "username" in update_data:
        existing = db.query(User).filter(
            User.username == update_data["username"],
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà pris"
            )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/me/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change le mot de passe de l'utilisateur connecté
    """
    # Vérifie l'ancien mot de passe
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )

    # Met à jour le mot de passe
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Mot de passe modifié avec succès"}


@router.delete("/me")
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Supprime le compte de l'utilisateur connecté
    """
    db.delete(current_user)
    db.commit()

    return {"message": "Compte supprimé avec succès"}


@router.get("/me/stats", response_model=ActivitySummary)
async def get_user_stats(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques d'utilisation de l'utilisateur
    """
    # Statistiques quotidiennes et hebdomadaires
    today_stats = get_daily_stats(db, current_user.id)
    week_stats = get_weekly_stats(db, current_user.id)

    # Calcule le progrès par rapport à la limite
    progress = calculate_progress_vs_limit(db, current_user)

    # App la plus addictive (plus de temps cette semaine)
    most_addictive = week_stats.top_apps[0].app_name if week_stats.top_apps else None

    # Compte total d'activités
    from app.models import Activity
    total_activities = db.query(Activity).filter(Activity.user_id == current_user.id).count()

    return ActivitySummary(
        today=today_stats,
        this_week=week_stats,
        total_activities=total_activities,
        most_addictive_app=most_addictive,
        progress_vs_limit=progress
    )


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les informations publiques d'un utilisateur par son ID
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    return user


@router.get("/search/{username}", response_model=List[UserPublic])
async def search_users(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    """
    Recherche des utilisateurs par nom d'utilisateur
    """
    users = db.query(User).filter(
        User.username.ilike(f"%{username}%"),
        User.is_active == True,
        User.is_verified == True
    ).limit(10).all()

    return users
