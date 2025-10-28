"""
Schémas Pydantic pour les logs
Système d'audit et de monitoring
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.log import LogLevel, LogAction


class LogBase(BaseModel):
    """Schéma de base pour un log"""
    action: LogAction
    level: LogLevel = LogLevel.INFO
    message: str = Field(..., min_length=1, max_length=255)
    details: Optional[str] = None


class LogCreate(LogBase):
    """Schéma pour créer un log"""
    user_id: Optional[int] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=255)
    endpoint: Optional[str] = Field(None, max_length=100)
    resource_type: Optional[str] = Field(None, max_length=50)
    resource_id: Optional[int] = None


class LogResponse(LogBase):
    """Schéma de réponse pour un log"""
    id: int
    user_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class LogFilter(BaseModel):
    """Filtres pour la recherche de logs"""
    user_id: Optional[int] = None
    action: Optional[LogAction] = None
    level: Optional[LogLevel] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None


class LogStats(BaseModel):
    """Statistiques des logs"""
    total_logs: int
    by_level: dict[str, int]
    by_action: dict[str, int]
    recent_errors: int
    unique_users: int


class LogListResponse(BaseModel):
    """Liste paginée de logs"""
    logs: list[LogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
