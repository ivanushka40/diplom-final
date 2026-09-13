import json
from dataclasses import dataclass
from os import getenv


def _cors_origins() -> list[str]:
    value = getenv("CORS_ORIGINS", '["http://localhost:5173","http://127.0.0.1:5173"]')
    try:
        origins = json.loads(value)
        return origins if isinstance(origins, list) else [str(origins)]
    except json.JSONDecodeError:
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("APP_NAME", "Nota API")
    root_path: str = getenv("ROOT_PATH", "")
    database_url: str = getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/nota"
    )
    secret_key: str = getenv("SECRET_KEY", "change-me-in-production")
    access_token_expire_minutes: int = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    cors_origins: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cors_origins", _cors_origins())


settings = Settings()
