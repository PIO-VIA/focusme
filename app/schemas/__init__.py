"""
Package schemas - Tous les schémas Pydantic de validation
"""
from app.schemas.user_schema import (
    UserBase,
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    UserPublic,
    UserAdmin,
    Token,
    TokenPayload,
    EmailVerification,
    PasswordResetRequest,
    PasswordReset,
    PasswordChange,
)

from app.schemas.activity_schema import (
    ActivityBase,
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityStats,
    DailyStats,
    WeeklyStats,
    ActivitySummary,
)

from app.schemas.challenge_schema import (
    ChallengeBase,
    ChallengeCreate,
    ChallengeUpdate,
    ChallengeResponse,
    ChallengeWithCreator,
    ChallengeParticipantBase,
    ChallengeParticipantResponse,
    ChallengeLeaderboard,
    ChallengeJoin,
    ChallengeResults,
    ChallengeListResponse,
)

from app.schemas.blocked_schema import (
    BlockedAppBase,
    BlockedAppCreate,
    BlockedAppUpdate,
    BlockedAppResponse,
    BlockedAppStatus,
    BlockStatusUpdate,
    BlockedAppsListResponse,
)

from app.schemas.log_schema import (
    LogBase,
    LogCreate,
    LogResponse,
    LogFilter,
    LogStats,
    LogListResponse,
)

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserResponse",
    "UserPublic",
    "UserAdmin",
    "Token",
    "TokenPayload",
    "EmailVerification",
    "PasswordResetRequest",
    "PasswordReset",
    "PasswordChange",
    # Activity
    "ActivityBase",
    "ActivityCreate",
    "ActivityUpdate",
    "ActivityResponse",
    "ActivityStats",
    "DailyStats",
    "WeeklyStats",
    "ActivitySummary",
    # Challenge
    "ChallengeBase",
    "ChallengeCreate",
    "ChallengeUpdate",
    "ChallengeResponse",
    "ChallengeWithCreator",
    "ChallengeParticipantBase",
    "ChallengeParticipantResponse",
    "ChallengeLeaderboard",
    "ChallengeJoin",
    "ChallengeResults",
    "ChallengeListResponse",
    # Blocked
    "BlockedAppBase",
    "BlockedAppCreate",
    "BlockedAppUpdate",
    "BlockedAppResponse",
    "BlockedAppStatus",
    "BlockStatusUpdate",
    "BlockedAppsListResponse",
    # Log
    "LogBase",
    "LogCreate",
    "LogResponse",
    "LogFilter",
    "LogStats",
    "LogListResponse",
]
