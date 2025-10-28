"""
Schémas Pydantic pour les challenges
Gestion des défis entre utilisateurs
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.challenge import ChallengeStatus, ChallengeType
from app.schemas.user_schema import UserPublic


class ChallengeBase(BaseModel):
    """Schéma de base pour un challenge"""
    title: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    challenge_type: ChallengeType = ChallengeType.MINIMIZE_TIME
    target_minutes: int = Field(..., ge=0, le=1440)


class ChallengeCreate(ChallengeBase):
    """Schéma pour créer un challenge"""
    start_date: datetime
    end_date: datetime
    max_participants: int = Field(default=10, ge=2, le=50)
    is_private: bool = False

    @validator('end_date')
    def validate_dates(cls, v, values):
        """Valide que end_date est après start_date"""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date doit être après start_date')

        # Vérifie que le challenge dure au moins 1 jour
        if 'start_date' in values:
            duration = (v - values['start_date']).days
            if duration < 1:
                raise ValueError('Le challenge doit durer au moins 1 jour')
            if duration > 30:
                raise ValueError('Le challenge ne peut pas durer plus de 30 jours')

        return v

    @validator('target_minutes')
    def validate_target(cls, v):
        """Valide que l'objectif est raisonnable"""
        if v < 0:
            raise ValueError('L\'objectif doit être positif')
        if v > 1440:  # 24 heures
            raise ValueError('L\'objectif ne peut pas dépasser 1440 minutes (24h)')
        return v


class ChallengeUpdate(BaseModel):
    """Schéma pour mettre à jour un challenge"""
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    status: Optional[ChallengeStatus] = None


class ChallengeResponse(ChallengeBase):
    """Schéma de réponse pour un challenge"""
    id: int
    creator_id: int
    status: ChallengeStatus
    start_date: datetime
    end_date: datetime
    max_participants: int
    is_private: bool
    invitation_code: Optional[str]
    winner_id: Optional[int]
    results_sent: bool
    created_at: datetime
    updated_at: datetime
    participants_count: Optional[int] = 0
    is_full: Optional[bool] = False

    class Config:
        from_attributes = True


class ChallengeWithCreator(ChallengeResponse):
    """Challenge avec les informations du créateur"""
    creator: UserPublic

    class Config:
        from_attributes = True


class ChallengeParticipantBase(BaseModel):
    """Schéma de base pour un participant"""
    challenge_id: int
    user_id: int


class ChallengeParticipantResponse(BaseModel):
    """Schéma de réponse pour un participant"""
    id: int
    challenge_id: int
    user_id: int
    total_time_minutes: float
    daily_average: float
    goal_achieved: bool
    score: float
    rank: Optional[int]
    joined_at: datetime
    is_active: bool
    user: UserPublic

    class Config:
        from_attributes = True


class ChallengeLeaderboard(BaseModel):
    """Classement du challenge"""
    challenge_id: int
    challenge_title: str
    status: ChallengeStatus
    participants: List[ChallengeParticipantResponse]
    total_participants: int


class ChallengeJoin(BaseModel):
    """Schéma pour rejoindre un challenge"""
    invitation_code: Optional[str] = None


class ChallengeResults(BaseModel):
    """Résultats finaux d'un challenge"""
    challenge_id: int
    challenge_title: str
    winner: Optional[UserPublic]
    leaderboard: List[ChallengeParticipantResponse]
    start_date: datetime
    end_date: datetime
    total_participants: int


class ChallengeListResponse(BaseModel):
    """Liste de challenges avec pagination"""
    challenges: List[ChallengeWithCreator]
    total: int
    page: int
    page_size: int
    total_pages: int
