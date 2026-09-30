from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
import app.models
from app.api.routes import (
    auth, companies, reviews, scores, rankings, categories, reports, admin, feed,
    review_interactions, notifications, battles,
)

app = FastAPI(
    title="AngoRating API",
    version="1.0.0",
    description="Plataforma de Rating e Reputação Angolana",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(reviews.router)
app.include_router(review_interactions.router)
app.include_router(notifications.router)
app.include_router(battles.router)
app.include_router(scores.router)
app.include_router(rankings.router)
app.include_router(categories.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(feed.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Erro interno do servidor",
            "code": "INTERNAL_ERROR",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
