from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings

# Pin env file to v3/python-api/ so a v1 .env at the repo root cannot leak
# its sync sqlite:/// URL into our async stack (loaded URLs need an async driver).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./omaha.db"
    secret_key: str = "dev-secret-change-in-production"
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str | None = None
    delta_storage: str = "./data/delta"
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    mcp_host: str = "0.0.0.0"
    mcp_port_start: int = 9000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}

    @field_validator("database_url")
    @classmethod
    def _ensure_async_driver(cls, v: str) -> str:
        # v1's `.env` ships `sqlite:///...` (sync). v3's SQLAlchemy is async.
        # Auto-rewrite so a leaked v1 env or a user typo doesn't 500 the whole API.
        if v.startswith("sqlite:///") and "+" not in v.split("://", 1)[0]:
            return v.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and "+" not in v.split("://", 1)[0]:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("mysql://") and "+" not in v.split("://", 1)[0]:
            return v.replace("mysql://", "mysql+aiomysql://", 1)
        return v


settings = Settings()
