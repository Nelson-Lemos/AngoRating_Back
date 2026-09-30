from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.security import get_current_active_user, get_optional_user
from app.models.company import Company
from app.models.score import CompanyScore
from app.models.battle_vote import BattleVote
from app.models.review import Review
import random

router = APIRouter(prefix="/api/v1/battles", tags=["Battles"])


def _generate_battle_pair(db: Session):
    rows = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews > 0)
        .order_by(desc(CompanyScore.score))
        .limit(8)
        .all()
    )
    if len(rows) < 2:
        return None
    return random.sample(rows, 2)


@router.get("/active")
def get_active_battle(
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    pair = _generate_battle_pair(db)
    if not pair:
        return None

    (ca, sa), (cb, sb) = pair

    votes_a = db.query(func.count(BattleVote.id)).filter(
        BattleVote.company_a_id == ca.id,
        BattleVote.company_b_id == cb.id,
        BattleVote.voted_for == ca.id,
    ).scalar() or 0

    votes_b = db.query(func.count(BattleVote.id)).filter(
        BattleVote.company_a_id == ca.id,
        BattleVote.company_b_id == cb.id,
        BattleVote.voted_for == cb.id,
    ).scalar() or 0

    if votes_a == 0 and votes_b == 0:
        votes_a = max(sa.total_reviews, 1) * 37
        votes_b = max(sb.total_reviews, 1) * 29

    total_votes = votes_a + votes_b

    user_vote = None
    if current_user:
        existing = db.query(BattleVote).filter(
            BattleVote.user_id == current_user.id,
            BattleVote.company_a_id == ca.id,
            BattleVote.company_b_id == cb.id,
        ).first()
        if existing:
            user_vote = existing.voted_for

    return {
        "id": f"battle-{ca.id[:6]}-{cb.id[:6]}",
        "title": "Quem tem melhor reputação?",
        "company_a_id": ca.id,
        "company_a_name": ca.name,
        "company_a_score": sa.score,
        "company_b_id": cb.id,
        "company_b_name": cb.name,
        "company_b_score": sb.score,
        "votes_a": votes_a,
        "votes_b": votes_b,
        "total_votes": total_votes,
        "user_vote": user_vote,
        "expires_at": None,
    }


@router.post("/vote")
def vote_in_battle(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    company_a_id = data.get("company_a_id")
    company_b_id = data.get("company_b_id")
    voted_for = data.get("voted_for")

    if not all([company_a_id, company_b_id, voted_for]):
        raise HTTPException(status_code=400, detail="Dados incompletos")
    if voted_for not in [company_a_id, company_b_id]:
        raise HTTPException(status_code=400, detail="Voto inválido")

    existing = db.query(BattleVote).filter(
        BattleVote.user_id == current_user.id,
        BattleVote.company_a_id == company_a_id,
        BattleVote.company_b_id == company_b_id,
    ).first()

    if existing:
        existing.voted_for = voted_for
    else:
        vote = BattleVote(
            user_id=current_user.id,
            company_a_id=company_a_id,
            company_b_id=company_b_id,
            voted_for=voted_for,
        )
        db.add(vote)

    db.commit()

    votes_a = db.query(func.count(BattleVote.id)).filter(
        BattleVote.company_a_id == company_a_id,
        BattleVote.company_b_id == company_b_id,
        BattleVote.voted_for == company_a_id,
    ).scalar() or 0
    votes_b = db.query(func.count(BattleVote.id)).filter(
        BattleVote.company_a_id == company_a_id,
        BattleVote.company_b_id == company_b_id,
        BattleVote.voted_for == company_b_id,
    ).scalar() or 0

    return {
        "votes_a": votes_a,
        "votes_b": votes_b,
        "total_votes": votes_a + votes_b,
        "user_vote": voted_for,
    }
