from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
import app.models
from app.api.routes import (
    auth, companies, reviews, scores, rankings, categories, reports, admin, feed,
    review_interactions, notifications,
)

app = FastAPI(
    title="AngoRating API",
    version="2.0.0",
    description="Plataforma angolana de reputação e descoberta de empresas",
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
app.include_router(scores.router)
app.include_router(rankings.router)
app.include_router(categories.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(feed.router)

# Imagens enviadas pela comunidade. `media_service` nunca escreve ficheiros com
# o nome do utilizador; o path é derivado do checksum.
settings.media_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.media_url,
    StaticFiles(directory=str(settings.media_dir)),
    name="media",
)


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
