"""
Schémas Pydantic pour les applications bloquées
Gestion des limites et blocages d'applications
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, time


class BlockedAppBase(BaseModel):
    """Schéma de base pour une application bloquée"""
    app_name: str = Field(..., min_length=1, max_length=100)
    app_package: Optional[str] = Field(None, max_length=255)
    app_category: str = Field(default="social_media", max_length=50)


class BlockedAppCreate(BlockedAppBase):
    """Schéma pour créer une application bloquée"""
    daily_limit_minutes: int = Field(default=60, ge=0, le=1440)
    block_start_time: Optional[time] = None
    block_end_time: Optional[time] = None
    block_on_weekends: bool = False
    notify_at_percentage: int = Field(default=80, ge=0, le=100)

    @validator('daily_limit_minutes')
    def validate_limit(cls, v):
        """Valide que la limite est raisonnable"""
        if v > 1440:
            raise ValueError('La limite quotidienne ne peut pas dépasser 1440 minutes (24h)')
        return v


class BlockedAppUpdate(BaseModel):
    """Schéma pour mettre à jour une application bloquée"""
    daily_limit_minutes: Optional[int] = Field(None, ge=0, le=1440)
    is_blocked: Optional[bool] = None
    block_start_time: Optional[time] = None
    block_end_time: Optional[time] = None
    block_on_weekends: Optional[bool] = None
    notify_at_percentage: Optional[int] = Field(None, ge=0, le=100)


class BlockedAppResponse(BlockedAppBase):
    """Schéma de réponse pour une application bloquée"""
    id: int
    user_id: int
    is_blocked: bool
    daily_limit_minutes: int
    current_usage_today: int
    block_start_time: Optional[time]
    block_end_time: Optional[time]
    block_on_weekends: bool
    notify_at_percentage: int
    notification_sent: bool
    created_at: datetime
    updated_at: datetime
    last_blocked_at: Optional[datetime]
    last_reset_at: Optional[datetime]
    usage_percentage: Optional[float] = None
    remaining_minutes: Optional[int] = None

    class Config:
        from_attributes = True


class BlockedAppStatus(BaseModel):
    """Statut actuel d'une application bloquée"""
    app_name: str
    is_blocked: bool
    usage_percentage: float
    remaining_minutes: int
    should_notify: bool


class BlockStatusUpdate(BaseModel):
    """Mise à jour du statut de blocage"""
    app_name: str
    additional_minutes: int = Field(..., ge=0)


class BlockedAppsListResponse(BaseModel):
    """Liste des applications bloquées"""
    blocked_apps: list[BlockedAppResponse]
    total: int
    total_blocked: int
    total_active: int
