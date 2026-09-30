from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models import user, company, category, location, review, score, ranking, report, fraud


def run_seeds():
    Base.metadata.create_all(bind=engine)
    from app.utils.seed import seed
    seed()


if __name__ == "__main__":
    run_seeds()
