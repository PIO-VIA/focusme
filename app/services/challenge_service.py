"""
Service de gestion des challenges
Calcule les scores, détermine les gagnants, etc.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from app.models import Challenge, ChallengeParticipant, Activity, User
from app.models.challenge import ChallengeStatus, ChallengeType
from app.utils.security import generate_invitation_code


def create_challenge(
    db: Session,
    creator_id: int,
    title: str,
    description: Optional[str],
    challenge_type: ChallengeType,
    target_minutes: int,
    start_date: datetime,
    end_date: datetime,
    max_participants: int,
    is_private: bool
) -> Challenge:
    """
    Crée un nouveau challenge

    Args:
        db: Session de base de données
        creator_id: ID du créateur
        title: Titre du challenge
        description: Description
        challenge_type: Type de challenge
        target_minutes: Objectif en minutes
        start_date: Date de début
        end_date: Date de fin
        max_participants: Nombre max de participants
        is_private: Challenge privé ou public

    Returns:
        Challenge: Challenge créé
    """
    # Génère un code d'invitation si le challenge est privé
    invitation_code = generate_invitation_code() if is_private else None

    challenge = Challenge(
        creator_id=creator_id,
        title=title,
        description=description,
        challenge_type=challenge_type,
        target_minutes=target_minutes,
        start_date=start_date,
        end_date=end_date,
        max_participants=max_participants,
        is_private=is_private,
        invitation_code=invitation_code,
        status=ChallengeStatus.PENDING
    )

    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    # Ajoute automatiquement le créateur comme participant
    join_challenge(db, challenge.id, creator_id)

    return challenge


def join_challenge(db: Session, challenge_id: int, user_id: int) -> ChallengeParticipant:
    """
    Permet à un utilisateur de rejoindre un challenge

    Args:
        db: Session de base de données
        challenge_id: ID du challenge
        user_id: ID de l'utilisateur

    Returns:
        ChallengeParticipant: Participant créé

    Raises:
        ValueError: Si le challenge est complet ou déjà commencé
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise ValueError("Challenge non trouvé")

    # Vérifie que le challenge n'est pas complet
    participant_count = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.is_active == True
    ).count()

    if participant_count >= challenge.max_participants:
        raise ValueError("Challenge complet")

    # Vérifie que l'utilisateur n'est pas déjà participant
    existing = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.user_id == user_id,
        ChallengeParticipant.is_active == True
    ).first()

    if existing:
        raise ValueError("Vous participez déjà à ce challenge")

    # Crée le participant
    participant = ChallengeParticipant(
        challenge_id=challenge_id,
        user_id=user_id,
        total_time_minutes=0.0,
        daily_average=0.0,
        score=0.0,
        is_active=True
    )

    db.add(participant)

    # Active le challenge s'il atteint 2 participants et que la date de début est passée
    if participant_count + 1 >= 2 and challenge.start_date <= datetime.utcnow():
        challenge.status = ChallengeStatus.ACTIVE

    db.commit()
    db.refresh(participant)

    return participant


def leave_challenge(db: Session, challenge_id: int, user_id: int) -> bool:
    """
    Permet à un utilisateur de quitter un challenge

    Args:
        db: Session de base de données
        challenge_id: ID du challenge
        user_id: ID de l'utilisateur

    Returns:
        bool: True si réussi
    """
    participant = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.user_id == user_id
    ).first()

    if participant:
        participant.is_active = False
        db.commit()
        return True

    return False


def calculate_participant_stats(
    db: Session,
    challenge: Challenge,
    participant: ChallengeParticipant
) -> None:
    """
    Calcule les statistiques d'un participant pour un challenge

    Args:
        db: Session de base de données
        challenge: Challenge
        participant: Participant
    """
    # Récupère toutes les activités pendant la période du challenge
    activities = db.query(Activity).filter(
        Activity.user_id == participant.user_id,
        Activity.activity_date >= challenge.start_date.date(),
        Activity.activity_date <= challenge.end_date.date()
    ).all()

    # Calcule le temps total
    total_minutes = sum(activity.duration_minutes for activity in activities)
    participant.total_time_minutes = total_minutes

    # Calcule la moyenne quotidienne
    duration_days = (challenge.end_date.date() - challenge.start_date.date()).days + 1
    participant.daily_average = total_minutes / duration_days if duration_days > 0 else 0

    # Calcule le score selon le type de challenge
    if challenge.challenge_type == ChallengeType.MINIMIZE_TIME:
        # Moins de temps = meilleur score
        # Score inversé: plus on utilise, moins on a de points
        max_possible = challenge.target_minutes * duration_days
        participant.score = max(0, max_possible - total_minutes)
        participant.goal_achieved = total_minutes <= (challenge.target_minutes * duration_days)
    else:
        # Pour les autres types, on pourra implémenter d'autres logiques
        participant.score = max(0, (challenge.target_minutes * duration_days) - total_minutes)
        participant.goal_achieved = participant.daily_average <= challenge.target_minutes

    db.commit()


def update_challenge_stats(db: Session, challenge_id: int) -> None:
    """
    Met à jour les statistiques de tous les participants d'un challenge

    Args:
        db: Session de base de données
        challenge_id: ID du challenge
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        return

    participants = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.is_active == True
    ).all()

    # Calcule les stats pour chaque participant
    for participant in participants:
        calculate_participant_stats(db, challenge, participant)

    # Trie par score (décroissant) et attribue les rangs
    participants = sorted(participants, key=lambda p: p.score, reverse=True)
    for rank, participant in enumerate(participants, start=1):
        participant.rank = rank

    db.commit()


def complete_challenge(db: Session, challenge_id: int) -> Optional[int]:
    """
    Termine un challenge et détermine le gagnant

    Args:
        db: Session de base de données
        challenge_id: ID du challenge

    Returns:
        Optional[int]: ID du gagnant, ou None
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        return None

    # Met à jour les statistiques finales
    update_challenge_stats(db, challenge_id)

    # Trouve le gagnant (rank = 1)
    winner = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.rank == 1,
        ChallengeParticipant.is_active == True
    ).first()

    if winner:
        challenge.winner_id = winner.user_id

    challenge.status = ChallengeStatus.COMPLETED
    db.commit()

    return winner.user_id if winner else None


def get_challenge_leaderboard(db: Session, challenge_id: int) -> List[Dict[str, Any]]:
    """
    Récupère le classement d'un challenge

    Args:
        db: Session de base de données
        challenge_id: ID du challenge

    Returns:
        List[Dict]: Liste des participants avec leurs stats
    """
    participants = db.query(ChallengeParticipant, User).join(
        User, ChallengeParticipant.user_id == User.id
    ).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.is_active == True
    ).order_by(ChallengeParticipant.rank.asc()).all()

    leaderboard = []
    for participant, user in participants:
        leaderboard.append({
            "rank": participant.rank,
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "total_time_minutes": participant.total_time_minutes,
            "daily_average": participant.daily_average,
            "score": participant.score,
            "goal_achieved": participant.goal_achieved
        })

    return leaderboard


def get_active_challenges_for_user(db: Session, user_id: int) -> List[Challenge]:
    """
    Récupère tous les challenges actifs d'un utilisateur

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur

    Returns:
        List[Challenge]: Liste des challenges actifs
    """
    challenges = db.query(Challenge).join(
        ChallengeParticipant,
        Challenge.id == ChallengeParticipant.challenge_id
    ).filter(
        ChallengeParticipant.user_id == user_id,
        ChallengeParticipant.is_active == True,
        Challenge.status == ChallengeStatus.ACTIVE
    ).all()

    return challenges


def check_and_complete_finished_challenges(db: Session) -> List[int]:
    """
    Vérifie et termine automatiquement les challenges terminés
    À appeler périodiquement (ex: toutes les heures)

    Args:
        db: Session de base de données

    Returns:
        List[int]: Liste des IDs des challenges terminés
    """
    now = datetime.utcnow()

    # Trouve tous les challenges actifs qui sont terminés
    finished_challenges = db.query(Challenge).filter(
        Challenge.status == ChallengeStatus.ACTIVE,
        Challenge.end_date <= now
    ).all()

    completed_ids = []
    for challenge in finished_challenges:
        winner_id = complete_challenge(db, challenge.id)
        completed_ids.append(challenge.id)

    return completed_ids


def check_and_start_pending_challenges(db: Session) -> List[int]:
    """
    Vérifie et démarre automatiquement les challenges en attente
    À appeler périodiquement

    Args:
        db: Session de base de données

    Returns:
        List[int]: Liste des IDs des challenges démarrés
    """
    now = datetime.utcnow()

    # Trouve tous les challenges en attente qui doivent commencer
    pending_challenges = db.query(Challenge).filter(
        Challenge.status == ChallengeStatus.PENDING,
        Challenge.start_date <= now
    ).all()

    started_ids = []
    for challenge in pending_challenges:
        # Vérifie qu'il y a au moins 2 participants
        participant_count = db.query(ChallengeParticipant).filter(
            ChallengeParticipant.challenge_id == challenge.id,
            ChallengeParticipant.is_active == True
        ).count()

        if participant_count >= 2:
            challenge.status = ChallengeStatus.ACTIVE
            started_ids.append(challenge.id)

    db.commit()
    return started_ids
