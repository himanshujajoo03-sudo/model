"""
FastAPI configuration from environment variables.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.environ.get("DATABASE_URL", "")
    kafka_bootstrap: str = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", "")
    jwt_expiration_hours: int = int(os.environ.get("JWT_EXPIRATION_HOURS", "8"))
    admin_username: str = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password: str = os.environ.get("ADMIN_PASSWORD", "")
    cors_origins: str = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    )
    media_upload_path: str = os.environ.get("MEDIA_UPLOAD_PATH", "/data/media")


settings = Settings()
