from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ─────────────────────────────────────────────────────────────
    # DATABASE
    # ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/angorating"
    )

    # ─────────────────────────────────────────────────────────────
    # SECURITY / JWT
    # ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    JWT_SECRET: str = "change-this-to-a-random-jwt-secret"
    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─────────────────────────────────────────────────────────────
    # CORS
    # ─────────────────────────────────────────────────────────────
    #
    # Desenvolvimento:
    #   http://localhost:5173
    #   http://localhost:3000
    #
    # Produção:
    #   https://angorating-six.vercel.app
    #
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "https://angorating-six.vercel.app"
    )

    ENVIRONMENT: str = "development"

    # ─────────────────────────────────────────────────────────────
    # MEDIA / UPLOADS
    # ─────────────────────────────────────────────────────────────
    MEDIA_ROOT: str = "./media"

    MEDIA_URL_PREFIX: str = "/media"

    MEDIA_MAX_UPLOAD_MB: int = 12

    MEDIA_MAX_DIMENSION: int = 6000

    MEDIA_MIN_DIMENSION: int = 320

    MEDIA_ALLOWED_MIME: str = (
        "image/jpeg,"
        "image/png,"
        "image/webp"
    )

    MEDIA_VARIANTS: str = "160,320,640,1280"

    # ─────────────────────────────────────────────────────────────
    # RATE LIMITING
    # ─────────────────────────────────────────────────────────────
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 8

    RATE_LIMIT_REGISTER_PER_HOUR: int = 5

    RATE_LIMIT_WRITE_PER_MINUTE: int = 30

    # ─────────────────────────────────────────────────────────────
    # REVIEWER REPUTATION
    # ─────────────────────────────────────────────────────────────
    REVIEWER_NEW_ACCOUNT_DAYS: int = 3

    REVIEW_DAILY_LIMIT: int = 20

    # ─────────────────────────────────────────────────────────────
    # CORS LIST
    # ─────────────────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    # ─────────────────────────────────────────────────────────────
    # MEDIA
    # ─────────────────────────────────────────────────────────────
    @property
    def media_max_bytes(self) -> int:
        return self.MEDIA_MAX_UPLOAD_MB * 1024 * 1024

    @property
    def media_allowed_mime_list(self) -> List[str]:
        return [
            mime.strip()
            for mime in self.MEDIA_ALLOWED_MIME.split(",")
            if mime.strip()
        ]

    @property
    def media_variants_list(self) -> List[int]:
        try:
            return [
                int(value)
                for value in self.MEDIA_VARIANTS.split(",")
                if value.strip()
            ]
        except ValueError:
            return [160, 320, 640, 1280]

    @property
    def media_dir(self) -> Path:
        return Path(self.MEDIA_ROOT).resolve()

    @property
    def media_url(self) -> str:
        return "/" + self.MEDIA_URL_PREFIX.strip("/")

    # ─────────────────────────────────────────────────────────────
    # PYDANTIC SETTINGS
    # ─────────────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()