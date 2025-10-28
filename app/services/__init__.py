"""
Package services - Services métier de l'application
"""
from app.services.email_service import (
    send_email,
    send_verification_email,
    send_password_reset_email,
    send_daily_reminder_email,
    send_challenge_results_email,
    send_limit_warning_email,
)

from app.services.log_service import (
    create_log,
    log_user_login,
    log_user_register,
    log_email_verified,
    log_password_reset_requested,
    log_password_reset_completed,
    log_app_blocked,
    log_limit_reached,
    log_challenge_created,
    log_challenge_joined,
    log_challenge_completed,
    log_user_deleted,
    log_admin_access,
    log_email_sent,
)

from app.services.timer_service import (
    calculate_daily_usage,
    calculate_app_usage_today,
    get_daily_stats,
    get_weekly_stats,
    get_app_stats,
    check_and_update_blocked_apps,
    reset_daily_limits,
    get_time_until_unblock,
    calculate_progress_vs_limit,
)

from app.services.challenge_service import (
    create_challenge,
    join_challenge,
    leave_challenge,
    calculate_participant_stats,
    update_challenge_stats,
    complete_challenge,
    get_challenge_leaderboard,
    get_active_challenges_for_user,
    check_and_complete_finished_challenges,
    check_and_start_pending_challenges,
)

__all__ = [
    # Email
    "send_email",
    "send_verification_email",
    "send_password_reset_email",
    "send_daily_reminder_email",
    "send_challenge_results_email",
    "send_limit_warning_email",
    # Log
    "create_log",
    "log_user_login",
    "log_user_register",
    "log_email_verified",
    "log_password_reset_requested",
    "log_password_reset_completed",
    "log_app_blocked",
    "log_limit_reached",
    "log_challenge_created",
    "log_challenge_joined",
    "log_challenge_completed",
    "log_user_deleted",
    "log_admin_access",
    "log_email_sent",
    # Timer
    "calculate_daily_usage",
    "calculate_app_usage_today",
    "get_daily_stats",
    "get_weekly_stats",
    "get_app_stats",
    "check_and_update_blocked_apps",
    "reset_daily_limits",
    "get_time_until_unblock",
    "calculate_progress_vs_limit",
    # Challenge
    "create_challenge",
    "join_challenge",
    "leave_challenge",
    "calculate_participant_stats",
    "update_challenge_stats",
    "complete_challenge",
    "get_challenge_leaderboard",
    "get_active_challenges_for_user",
    "check_and_complete_finished_challenges",
    "check_and_start_pending_challenges",
]
