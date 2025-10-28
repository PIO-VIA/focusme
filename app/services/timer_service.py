"""
Service de gestion du temps
Calcule les statistiques d'utilisation et vérifie les limites
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from app.models import Activity, BlockedApp, User
from app.schemas.activity_schema import ActivityStats, DailyStats, WeeklyStats


def calculate_daily_usage(db: Session, user_id: int, target_date: date = None) -> float:
    """
    Calcule le temps total d'utilisation pour un jour donné

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        target_date: Date cible (par défaut aujourd'hui)

    Returns:
        float: Temps total en minutes
    """
    if not target_date:
        target_date = date.today()

    total = db.query(func.sum(Activity.duration_minutes)).filter(
        Activity.user_id == user_id,
        Activity.activity_date == target_date
    ).scalar()

    return total or 0.0


def calculate_app_usage_today(db: Session, user_id: int, app_name: str) -> float:
    """
    Calcule l'utilisation d'une application aujourd'hui

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        app_name: Nom de l'application

    Returns:
        float: Temps d'utilisation en minutes
    """
    today = date.today()

    total = db.query(func.sum(Activity.duration_minutes)).filter(
        Activity.user_id == user_id,
        Activity.app_name == app_name,
        Activity.activity_date == today
    ).scalar()

    return total or 0.0


def get_daily_stats(db: Session, user_id: int, target_date: date = None) -> DailyStats:
    """
    Récupère les statistiques quotidiennes

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        target_date: Date cible (par défaut aujourd'hui)

    Returns:
        DailyStats: Statistiques du jour
    """
    if not target_date:
        target_date = date.today()

    # Total du jour
    total_minutes = calculate_daily_usage(db, user_id, target_date)

    # Nombre d'apps utilisées
    apps_used = db.query(func.count(func.distinct(Activity.app_name))).filter(
        Activity.user_id == user_id,
        Activity.activity_date == target_date
    ).scalar() or 0

    # App la plus utilisée
    most_used = db.query(
        Activity.app_name,
        func.sum(Activity.duration_minutes).label("total")
    ).filter(
        Activity.user_id == user_id,
        Activity.activity_date == target_date
    ).group_by(Activity.app_name).order_by(func.sum(Activity.duration_minutes).desc()).first()

    return DailyStats(
        date=target_date,
        total_minutes=total_minutes,
        total_hours=round(total_minutes / 60, 2),
        apps_used=apps_used,
        most_used_app=most_used[0] if most_used else None,
        most_used_app_minutes=most_used[1] if most_used else None
    )


def get_weekly_stats(db: Session, user_id: int) -> WeeklyStats:
    """
    Récupère les statistiques hebdomadaires

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur

    Returns:
        WeeklyStats: Statistiques de la semaine
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=6)  # 7 derniers jours

    # Total de la semaine
    total_minutes = db.query(func.sum(Activity.duration_minutes)).filter(
        Activity.user_id == user_id,
        Activity.activity_date >= start_date,
        Activity.activity_date <= end_date
    ).scalar() or 0.0

    # Nombre d'apps utilisées
    apps_used = db.query(func.count(func.distinct(Activity.app_name))).filter(
        Activity.user_id == user_id,
        Activity.activity_date >= start_date,
        Activity.activity_date <= end_date
    ).scalar() or 0

    # Top apps
    top_apps_query = db.query(
        Activity.app_name,
        func.sum(Activity.duration_minutes).label("total_minutes"),
        func.count(Activity.id).label("session_count")
    ).filter(
        Activity.user_id == user_id,
        Activity.activity_date >= start_date,
        Activity.activity_date <= end_date
    ).group_by(Activity.app_name).order_by(func.sum(Activity.duration_minutes).desc()).limit(5).all()

    top_apps = [
        ActivityStats(
            app_name=app[0],
            total_minutes=app[1],
            total_hours=round(app[1] / 60, 2),
            session_count=app[2],
            average_session_minutes=round(app[1] / app[2], 2) if app[2] > 0 else 0,
            last_used=None
        )
        for app in top_apps_query
    ]

    return WeeklyStats(
        start_date=start_date,
        end_date=end_date,
        total_minutes=total_minutes,
        total_hours=round(total_minutes / 60, 2),
        daily_average_minutes=round(total_minutes / 7, 2),
        apps_used=apps_used,
        top_apps=top_apps
    )


def get_app_stats(db: Session, user_id: int, app_name: str) -> ActivityStats:
    """
    Récupère les statistiques pour une application spécifique

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        app_name: Nom de l'application

    Returns:
        ActivityStats: Statistiques de l'application
    """
    # Total et nombre de sessions
    stats = db.query(
        func.sum(Activity.duration_minutes).label("total_minutes"),
        func.count(Activity.id).label("session_count"),
        func.max(Activity.created_at).label("last_used")
    ).filter(
        Activity.user_id == user_id,
        Activity.app_name == app_name
    ).first()

    total_minutes = stats[0] or 0.0
    session_count = stats[1] or 0
    last_used = stats[2]

    return ActivityStats(
        app_name=app_name,
        total_minutes=total_minutes,
        total_hours=round(total_minutes / 60, 2),
        session_count=session_count,
        average_session_minutes=round(total_minutes / session_count, 2) if session_count > 0 else 0,
        last_used=last_used
    )


def check_and_update_blocked_apps(db: Session, user_id: int) -> List[BlockedApp]:
    """
    Vérifie toutes les apps bloquées et met à jour leur statut

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur

    Returns:
        List[BlockedApp]: Liste des apps qui doivent être bloquées
    """
    blocked_apps = db.query(BlockedApp).filter(BlockedApp.user_id == user_id).all()
    apps_to_block = []

    for blocked_app in blocked_apps:
        # Calcule l'utilisation actuelle
        current_usage = calculate_app_usage_today(db, user_id, blocked_app.app_name)
        blocked_app.current_usage_today = int(current_usage)

        # Vérifie si l'app doit être bloquée
        if current_usage >= blocked_app.daily_limit_minutes:
            if not blocked_app.is_blocked:
                blocked_app.is_blocked = True
                blocked_app.last_blocked_at = datetime.utcnow()
                apps_to_block.append(blocked_app)

        # Vérifie si une notification doit être envoyée
        usage_percentage = (current_usage / blocked_app.daily_limit_minutes * 100) if blocked_app.daily_limit_minutes > 0 else 0
        if usage_percentage >= blocked_app.notify_at_percentage and not blocked_app.notification_sent:
            blocked_app.notification_sent = True

    db.commit()
    return apps_to_block


def reset_daily_limits(db: Session) -> None:
    """
    Réinitialise les compteurs quotidiens pour tous les utilisateurs
    À appeler à minuit chaque jour

    Args:
        db: Session de base de données
    """
    blocked_apps = db.query(BlockedApp).all()

    for blocked_app in blocked_apps:
        blocked_app.current_usage_today = 0
        blocked_app.is_blocked = False
        blocked_app.notification_sent = False
        blocked_app.last_reset_at = datetime.utcnow()

    db.commit()


def get_time_until_unblock(blocked_app: BlockedApp) -> Optional[int]:
    """
    Calcule le temps restant avant déblocage (en secondes)

    Args:
        blocked_app: Application bloquée

    Returns:
        Optional[int]: Secondes restantes jusqu'à minuit, ou None si pas bloquée
    """
    if not blocked_app.is_blocked:
        return None

    now = datetime.utcnow()
    midnight = datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
    seconds_until_midnight = (midnight - now).total_seconds()

    return int(seconds_until_midnight)


def calculate_progress_vs_limit(db: Session, user: User) -> float:
    """
    Calcule le pourcentage d'utilisation par rapport à la limite quotidienne de l'utilisateur

    Args:
        db: Session de base de données
        user: Utilisateur

    Returns:
        float: Pourcentage (0-100+)
    """
    today_usage = calculate_daily_usage(db, user.id)

    if user.daily_limit_minutes == 0:
        return 100.0

    percentage = (today_usage / user.daily_limit_minutes) * 100
    return round(percentage, 2)
