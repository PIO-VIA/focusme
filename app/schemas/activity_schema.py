"""
Schémas Pydantic pour les activités
Suivi du temps d'utilisation des applications
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date


class ActivityBase(BaseModel):
    """Schéma de base pour une activité"""
    app_name: str = Field(..., min_length=1, max_length=100)
    app_package: Optional[str] = Field(None, max_length=255)
    app_category: str = Field(default="social_media", max_length=50)


class ActivityCreate(ActivityBase):
    """Schéma pour créer une activité"""
    duration_minutes: float = Field(..., ge=0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    activity_date: Optional[date] = None
    device_type: Optional[str] = Field(None, max_length=50)
    session_id: Optional[str] = Field(None, max_length=100)

    @validator('duration_minutes')
    def validate_duration(cls, v):
        """Valide que la durée est raisonnable (max 24h)"""
        if v > 1440:  # 24 heures
            raise ValueError('La durée ne peut pas dépasser 24 heures (1440 minutes)')
        return v

    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Valide que end_time est après start_time"""
        if v and 'start_time' in values and values['start_time']:
            if v < values['start_time']:
                raise ValueError('end_time doit être après start_time')
        return v


class ActivityUpdate(BaseModel):
    """Schéma pour mettre à jour une activité"""
    duration_minutes: Optional[float] = Field(None, ge=0)
    end_time: Optional[datetime] = None

    @validator('duration_minutes')
    def validate_duration(cls, v):
        if v and v > 1440:
            raise ValueError('La durée ne peut pas dépasser 24 heures (1440 minutes)')
        return v


class ActivityResponse(ActivityBase):
    """Schéma de réponse pour une activité"""
    id: int
    user_id: int
    duration_minutes: float
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    activity_date: date
    device_type: Optional[str]
    session_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivityStats(BaseModel):
    """Statistiques d'utilisation"""
    app_name: str
    total_minutes: float
    total_hours: float
    session_count: int
    average_session_minutes: float
    last_used: Optional[datetime]


class DailyStats(BaseModel):
    """Statistiques quotidiennes"""
    date: date
    total_minutes: float
    total_hours: float
    apps_used: int
    most_used_app: Optional[str]
    most_used_app_minutes: Optional[float]


class WeeklyStats(BaseModel):
    """Statistiques hebdomadaires"""
    start_date: date
    end_date: date
    total_minutes: float
    total_hours: float
    daily_average_minutes: float
    apps_used: int
    top_apps: list[ActivityStats]


class ActivitySummary(BaseModel):
    """Résumé complet des activités"""
    today: DailyStats
    this_week: WeeklyStats
    total_activities: int
    most_addictive_app: Optional[str]
    progress_vs_limit: float  # Pourcentage par rapport à la limite quotidienne
