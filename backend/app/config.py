"""
FastAPI application configuration.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "Omaha OntoCenter"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # DataHub
    DATAHUB_GMS_URL: str
    DATAHUB_GMS_TOKEN: Optional[str] = None

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # LLM
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Tushare
    TUSHARE_TOKEN: Optional[str] = None

    # Inference
    INFER_LLM_PROVIDER: str = "deepseek"
    INFER_MAX_RETRIES: int = 1
    INFER_TIMEOUT: int = 30
    INFER_SAMPLE_ROWS: int = 500
    INFER_DISTINCT_LIMIT: int = 20

    model_config = SettingsConfigDict(env_file="../.env", case_sensitive=True)


settings = Settings(_env_file="../.env")
