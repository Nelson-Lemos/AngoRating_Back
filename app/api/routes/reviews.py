from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user, get_optional_user
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services import review_service, scoring_service, moderation_service

router = APIRouter(prefix="/api/v1", tags=["Reviews"])


@router.get("/companies/{company_id}/reviews/distribution", response_model=dict)
def get_reviews_distribution(
    company_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    from app.models.review import Review

    review_rows = (
        db.query(Review)
        .filter(Review.company_id == company_id, Review.is_valid == True)
        .all()
    )

    total = len(review_rows)
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_score = 0.0

    def star_avg(r):
        return round((r.quality + r.service + r.price + r.reliability + r.experience) / 5)

    for r in review_rows:
        stars = star_avg(r)
        distribution[stars] += 1
        total_score += stars

    dist_payload = []
    for stars in range(5, 0, -1):
        count = distribution[stars]
        pct = round((count / total) * 100, 1) if total else 0.0
        dist_payload.append({"stars": stars, "count": count, "percentage": pct})

    average = round(total_score / total, 1) if total else 0.0

    user_vote = None
    community_agreement = None
    if total and current_user:
        mine = next((r for r in review_rows if r.user_id == current_user.id), None)
        if mine:
            user_vote = star_avg(mine)
            user_pct = round((distribution[user_vote] / total) * 100, 1) if distribution.get(user_vote) else 0.0
            community_agreement = user_pct

    return {
        "total_reviews": total,
        "average": average,
        "distribution": dist_payload,
        "user_vote": user_vote,
        "community_agreement": community_agreement,
    }


@router.post("/companies/{company_id}/reviews", response_model=dict, status_code=201)
def create_review(
    company_id: str,
    data: ReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    data.company_id = company_id
    mode = data.__dict__.get("mode", "new")

    from app.models.review import Review

    existing = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.company_id == company_id,
        Review.is_valid == True,
    ).first()

    if mode == "update" and existing:
        try:
            review = review_service.update_review(db, current_user.id, company_id, data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        scoring_service.recalculate_score(db, company_id)
        return {
            "id": review.id,
            "mode": "updated",
            "message": "Avaliação actualizada com sucesso",
            "quality": review.quality,
            "service": review.service,
            "price": review.price,
            "reliability": review.reliability,
            "experience": review.experience,
        }

    fraud_check = moderation_service.check_review_allowed(
        db, current_user.id, company_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if not fraud_check["allowed"]:
        for issue in fraud_check["issues"]:
            moderation_service.record_fraud_signal(
                db, current_user.id, company_id, issue,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        raise HTTPException(status_code=403, detail="Avaliação bloqueada pelo sistema de segurança")

    try:
        review = review_service.create_review(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    scoring_service.recalculate_score(db, company_id)

    return {
        "id": review.id,
        "mode": "created",
        "message": "Avaliação registrada com sucesso",
        "quality": review.quality,
        "service": review.service,
        "price": review.price,
        "reliability": review.reliability,
        "experience": review.experience,
    }


@router.get("/companies/{company_id}/reviews", response_model=dict)
def get_company_reviews(
    company_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total, items = review_service.get_company_reviews(db, company_id, skip, limit)

    from app.models.review_vote import ReviewVote, ReviewComment

    review_ids = [r.id for r in items]
    vote_counts = {}
    if review_ids:
        votes = (
            db.query(
                ReviewVote.review_id,
                ReviewVote.is_agree,
                func.count(ReviewVote.id),
            )
            .filter(ReviewVote.review_id.in_(review_ids))
            .group_by(ReviewVote.review_id, ReviewVote.is_agree)
            .all()
        )
        for rid, is_agree, cnt in votes:
            key = rid
            vote_counts.setdefault(key, {"agree": 0, "disagree": 0})
            if is_agree:
                vote_counts[key]["agree"] = cnt
            else:
                vote_counts[key]["disagree"] = cnt

    comment_counts = {}
    if review_ids:
        cc = (
            db.query(ReviewComment.review_id, func.count(ReviewComment.id))
            .filter(ReviewComment.review_id.in_(review_ids))
            .group_by(ReviewComment.review_id)
            .all()
        )
        for rid, cnt in cc:
            comment_counts[rid] = cnt

    payload = []
    for r in items:
        vc = vote_counts.get(r.id, {"agree": 0, "disagree": 0})
        payload.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_name": r.user.name if r.user else None,
            "quality": r.quality,
            "service": r.service,
            "price": r.price,
            "reliability": r.reliability,
            "experience": r.experience,
            "agree_count": vc["agree"],
            "disagree_count": vc["disagree"],
            "comment_count": comment_counts.get(r.id, 0),
            "created_at": r.created_at,
        })

    return {"total": total, "items": payload}


@router.get("/users/me/reviews", response_model=dict)
def get_my_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    total, items = review_service.get_user_reviews(db, current_user.id, skip, limit)
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "company_id": r.company_id,
                "company_name": r.company.name if r.company else None,
                "quality": r.quality,
                "service": r.service,
                "price": r.price,
                "reliability": r.reliability,
                "experience": r.experience,
                "created_at": r.created_at,
            }
            for r in items
        ],
    }
