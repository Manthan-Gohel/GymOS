from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GymOS"
    app_env: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./gymos.db"
    redis_url: str = "redis://localhost:6379/0"

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

    # LLM (Chatbot)
    llm_enabled: bool = False
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
