from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/campus_rag"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    CONFIG_ENCRYPTION_KEY: str = "change-this-to-a-random-key"
    FILE_STORAGE_PATH: str = "./backend/uploads"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
