from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRETS = {"change-me", "change-me-in-dev", "secret", "changeme"}


class Settings(BaseSettings):
    app_name: str = "GymOS"
    app_env: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./gymos.db"
    redis_url: str = "redis://localhost:6379/0"

    # Auth / web
    # ponytail: dev-only defaults; production must set CORS_ORIGINS + COOKIE_SECURE=true
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cookie_secure: bool = False
    login_rate_limit_per_minute: int = 10

    # Messaging (openWA)
    messaging_provider: str = "mock"
    openwa_base_url: str = "http://localhost:8080"
    openwa_api_key: str = ""
    openwa_session_id: str = "default"
    openwa_webhook_secret: str = ""

    # Payments (YouPI-PG)
    payments_provider: str = "mock"
    youpi_base_url: str = "http://localhost:3000"
    youpi_merchant_key: str = ""
    youpi_webhook_secret: str = ""

    # LLM (Chatbot). For local LLM: provider=ollama, base_url=http://localhost:11434/v1
    llm_enabled: bool = False
    llm_provider: str = "ollama"
    llm_api_key: str = ""
    llm_model: str = "llama3.1"
    llm_base_url: str = "http://localhost:11434/v1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("secret_key")
    @classmethod
    def _reject_insecure_secret_in_prod(cls, v: str, info) -> str:
        env = (info.data.get("app_env") or "development").lower()
        if env in {"production", "staging"}:
            if v in INSECURE_DEFAULT_SECRETS or len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be a unique value of at least 32 characters in production/staging"
                )
        return v


settings = Settings()
