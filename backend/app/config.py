from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "BlastWave SMS"
    app_url: str = "http://localhost:3000"
    webhook_base_url: str = "http://localhost:8000"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://blastwave:blastwave@localhost:5432/blastwave"
    database_url_sync: str = "postgresql://blastwave:blastwave@localhost:5432/blastwave"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Bandwidth
    bandwidth_account_id: str = ""
    bandwidth_api_token: str = ""
    bandwidth_api_secret: str = ""
    bandwidth_application_id: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_growth: str = ""
    stripe_price_enterprise: str = ""

    # AI
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # S3
    s3_bucket: str = "blastwave-media"
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""


@lru_cache()
def get_settings():
    return Settings()
