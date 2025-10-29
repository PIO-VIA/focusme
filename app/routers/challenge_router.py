"""
Router des challenges
Gère la création, la participation et le suivi des challenges entre amis
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User, Challenge, ChallengeParticipant
from app.models.challenge import ChallengeStatus, ChallengeType
from app.schemas.challenge_schema import (
    ChallengeCreate,
    ChallengeResponse,
    ChallengeDetailResponse,
    ChallengeParticipantResponse,
    ChallengeJoin,
    ChallengeLeaderboard
)
from app.utils.jwt_handler import get_current_verified_user
from app.services import challenge_service
from app.services.log_service import log_challenge_created, log_challenge_joined, log_challenge_left
from app.services.email_service import send_challenge_results_email

router = APIRouter(prefix="/challenges", tags=["Challenges"])


@router.post("/", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
async def create_challenge(
    challenge_data: ChallengeCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Crée un nouveau challenge

    - Seuls les utilisateurs vérifiés peuvent créer des challenges
    - Le créateur est automatiquement ajouté comme participant
    - Un code d'invitation est généré pour les challenges privés
    """
    try:
        challenge = challenge_service.create_challenge(
            db=db,
            creator_id=current_user.id,
            title=challenge_data.title,
            description=challenge_data.description,
            challenge_type=challenge_data.challenge_type,
            target_minutes=challenge_data.target_minutes,
            start_date=challenge_data.start_date,
            end_date=challenge_data.end_date,
            max_participants=challenge_data.max_participants,
            is_private=challenge_data.is_private
        )

        # Log la création
        await log_challenge_created(db, current_user, challenge)

        return challenge

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[ChallengeResponse])
async def get_challenges(
    status_filter: Optional[ChallengeStatus] = Query(None, description="Filtrer par statut"),
    include_private: bool = Query(False, description="Inclure les challenges privés"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère la liste des challenges

    - Par défaut, affiche seulement les challenges publics
    - Peut filtrer par statut (pending, active, completed)
    """
    query = db.query(Challenge)

    if not include_private:
        query = query.filter(Challenge.is_private == False)

    if status_filter:
        query = query.filter(Challenge.status == status_filter)

    challenges = query.order_by(Challenge.created_at.desc()).all()
    return challenges


@router.get("/my-challenges", response_model=List[ChallengeResponse])
async def get_my_challenges(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère tous les challenges auxquels l'utilisateur participe
    """
    challenges = db.query(Challenge).join(
        ChallengeParticipant,
        Challenge.id == ChallengeParticipant.challenge_id
    ).filter(
        ChallengeParticipant.user_id == current_user.id,
        ChallengeParticipant.is_active == True
    ).order_by(Challenge.created_at.desc()).all()

    return challenges


@router.get("/{challenge_id}", response_model=ChallengeDetailResponse)
async def get_challenge_detail(
    challenge_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère les détails d'un challenge

    - Affiche les informations complètes
    - Inclut les participants et le classement
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge non trouvé"
        )

    # Vérifie l'accès pour les challenges privés
    if challenge.is_private:
        participant = db.query(ChallengeParticipant).filter(
            ChallengeParticipant.challenge_id == challenge_id,
            ChallengeParticipant.user_id == current_user.id,
            ChallengeParticipant.is_active == True
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé à ce challenge privé"
            )

    # Récupère les participants
    participants = db.query(ChallengeParticipant, User).join(
        User, ChallengeParticipant.user_id == User.id
    ).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.is_active == True
    ).order_by(ChallengeParticipant.rank.asc()).all()

    participants_data = [
        ChallengeParticipantResponse(
            id=p.id,
            user_id=u.id,
            username=u.username,
            full_name=u.full_name,
            avatar_url=u.avatar_url,
            total_time_minutes=p.total_time_minutes,
            daily_average=p.daily_average,
            score=p.score,
            rank=p.rank,
            goal_achieved=p.goal_achieved,
            joined_at=p.joined_at
        )
        for p, u in participants
    ]

    return ChallengeDetailResponse(
        **challenge.__dict__,
        participants=participants_data
    )


@router.post("/{challenge_id}/join", response_model=ChallengeParticipantResponse)
async def join_challenge(
    challenge_id: int,
    join_data: Optional[ChallengeJoin] = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Rejoint un challenge

    - Pour les challenges privés, nécessite un code d'invitation
    - Limite le nombre de participants selon max_participants
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge non trouvé"
        )

    # Vérifie le code d'invitation pour les challenges privés
    if challenge.is_private:
        if not join_data or join_data.invitation_code != challenge.invitation_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Code d'invitation invalide"
            )

    try:
        participant = challenge_service.join_challenge(db, challenge_id, current_user.id)

        # Log la participation
        await log_challenge_joined(db, current_user, challenge)

        # Récupère les infos de l'utilisateur pour la réponse
        user = db.query(User).filter(User.id == current_user.id).first()

        return ChallengeParticipantResponse(
            id=participant.id,
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            total_time_minutes=participant.total_time_minutes,
            daily_average=participant.daily_average,
            score=participant.score,
            rank=participant.rank,
            goal_achieved=participant.goal_achieved,
            joined_at=participant.joined_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{challenge_id}/leave")
async def leave_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Quitte un challenge

    - Le créateur ne peut pas quitter son propre challenge
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge non trouvé"
        )

    if challenge.creator_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le créateur ne peut pas quitter son propre challenge"
        )

    success = challenge_service.leave_challenge(db, challenge_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne participez pas à ce challenge"
        )

    # Log le départ
    await log_challenge_left(db, current_user, challenge)

    return {"message": "Vous avez quitté le challenge"}


@router.get("/{challenge_id}/leaderboard", response_model=List[ChallengeLeaderboard])
async def get_challenge_leaderboard(
    challenge_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Récupère le classement d'un challenge

    - Affiche tous les participants triés par rang
    - Met à jour les statistiques en temps réel pour les challenges actifs
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge non trouvé"
        )

    # Vérifie l'accès pour les challenges privés
    if challenge.is_private:
        participant = db.query(ChallengeParticipant).filter(
            ChallengeParticipant.challenge_id == challenge_id,
            ChallengeParticipant.user_id == current_user.id,
            ChallengeParticipant.is_active == True
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé à ce challenge privé"
            )

    # Met à jour les stats si le challenge est actif
    if challenge.status == ChallengeStatus.ACTIVE:
        challenge_service.update_challenge_stats(db, challenge_id)

    leaderboard = challenge_service.get_challenge_leaderboard(db, challenge_id)

    return [ChallengeLeaderboard(**entry) for entry in leaderboard]


@router.delete("/{challenge_id}")
async def delete_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Supprime un challenge

    - Seul le créateur peut supprimer son challenge
    - Ne peut supprimer que les challenges en attente (pas encore commencés)
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge non trouvé"
        )

    if challenge.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le créateur peut supprimer ce challenge"
        )

    if challenge.status != ChallengeStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer un challenge déjà commencé"
        )

    db.delete(challenge)
    db.commit()

    return {"message": "Challenge supprimé avec succès"}


@router.post("/{challenge_id}/complete")
async def complete_challenge_manually(
    challenge_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Termine manuellement un challenge (réservé au créateur)

    - Calcule le classement final
    - Envoie les emails de résultats aux participants
    """
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge non trouvé"
        )

    if challenge.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le créateur peut terminer manuellement ce challenge"
        )

    if challenge.status != ChallengeStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce challenge n'est pas actif"
        )

    # Termine le challenge
    winner_id = challenge_service.complete_challenge(db, challenge_id)

    # Envoie les emails de résultats
    participants = db.query(ChallengeParticipant, User).join(
        User, ChallengeParticipant.user_id == User.id
    ).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.is_active == True
    ).all()

    winner = db.query(User).filter(User.id == winner_id).first()
    winner_name = winner.username if winner else "N/A"

    for participant, user in participants:
        if user.email_reminders:
            await send_challenge_results_email(
                email=user.email,
                username=user.username,
                challenge_title=challenge.title,
                rank=participant.rank,
                total_participants=len(participants),
                winner_name=winner_name
            )

    # Marque les résultats comme envoyés
    challenge.results_sent = True
    db.commit()

    return {"message": "Challenge terminé et résultats envoyés", "winner_id": winner_id}
