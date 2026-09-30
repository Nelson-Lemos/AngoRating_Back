from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_active_user, get_optional_user
from app.models.social import ReviewVote, ReviewComment
from app.models.review import Review
from app.models.notification import Notification

router = APIRouter(prefix="/api/v1/reviews", tags=["Review Interactions"])


@router.post("/{review_id}/agree")
def agree_with_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    review = db.query(Review).filter(Review.id == review_id, Review.is_valid == True).first()
    if not review:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    if review.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Não pode votar na própria avaliação")

    existing = db.query(ReviewVote).filter(
        ReviewVote.user_id == current_user.id,
        ReviewVote.review_id == review_id,
    ).first()

    if existing:
        if existing.is_agree:
            db.delete(existing)
            db.commit()
        else:
            existing.is_agree = True
            db.commit()
    else:
        vote = ReviewVote(user_id=current_user.id, review_id=review_id, is_agree=True)
        db.add(vote)
        db.commit()

        if review.user_id != current_user.id:
            notif = Notification(
                user_id=review.user_id,
                type="review_agree",
                content=f"Alguém concordou com a sua avaliação",
                entity_type="review",
                entity_id=review_id,
            )
            db.add(notif)
            db.commit()

    agree_count = db.query(func.count(ReviewVote.id)).filter(
        ReviewVote.review_id == review_id, ReviewVote.is_agree == True
    ).scalar()
    disagree_count = db.query(func.count(ReviewVote.id)).filter(
        ReviewVote.review_id == review_id, ReviewVote.is_agree == False
    ).scalar()

    return {"agree_count": agree_count, "disagree_count": disagree_count}


@router.post("/{review_id}/disagree")
def disagree_with_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    review = db.query(Review).filter(Review.id == review_id, Review.is_valid == True).first()
    if not review:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    if review.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Não pode votar na própria avaliação")

    existing = db.query(ReviewVote).filter(
        ReviewVote.user_id == current_user.id,
        ReviewVote.review_id == review_id,
    ).first()

    if existing:
        if not existing.is_agree:
            db.delete(existing)
            db.commit()
        else:
            existing.is_agree = False
            db.commit()
    else:
        vote = ReviewVote(user_id=current_user.id, review_id=review_id, is_agree=False)
        db.add(vote)
        db.commit()

    agree_count = db.query(func.count(ReviewVote.id)).filter(
        ReviewVote.review_id == review_id, ReviewVote.is_agree == True
    ).scalar()
    disagree_count = db.query(func.count(ReviewVote.id)).filter(
        ReviewVote.review_id == review_id, ReviewVote.is_agree == False
    ).scalar()

    return {"agree_count": agree_count, "disagree_count": disagree_count}


@router.get("/{review_id}/stats")
def get_vote_stats(
    review_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    agree_count = db.query(func.count(ReviewVote.id)).filter(
        ReviewVote.review_id == review_id, ReviewVote.is_agree == True
    ).scalar()
    disagree_count = db.query(func.count(ReviewVote.id)).filter(
        ReviewVote.review_id == review_id, ReviewVote.is_agree == False
    ).scalar()

    user_vote = None
    if current_user:
        existing = db.query(ReviewVote).filter(
            ReviewVote.user_id == current_user.id,
            ReviewVote.review_id == review_id,
        ).first()
        if existing:
            user_vote = existing.is_agree

    return {"agree_count": agree_count, "disagree_count": disagree_count, "user_vote": user_vote}


@router.post("/{review_id}/comments")
def add_comment(
    review_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    review = db.query(Review).filter(Review.id == review_id, Review.is_valid == True).first()
    if not review:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")

    content = data.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Comentário não pode estar vazio")
    if len(content) > 500:
        raise HTTPException(status_code=400, detail="Comentário muito longo (máx. 500 caracteres)")

    comment = ReviewComment(user_id=current_user.id, review_id=review_id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    if review.user_id != current_user.id:
        notif = Notification(
            user_id=review.user_id,
            type="review_comment",
            content=f"Alguém comentou na sua avaliação",
            entity_type="review",
            entity_id=review_id,
        )
        db.add(notif)
        db.commit()

    return {
        "id": comment.id,
        "user_name": current_user.name,
        "content": comment.content,
        "created_at": comment.created_at,
    }


@router.get("/{review_id}/comments")
def get_comments(
    review_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(ReviewComment).filter(ReviewComment.review_id == review_id)
    total = query.count()
    items = query.order_by(ReviewComment.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": c.id,
                "user_name": c.user.name if c.user else "Anónimo",
                "content": c.content,
                "created_at": c.created_at,
            }
            for c in items
        ],
    }
