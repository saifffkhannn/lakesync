"""Application configuration loaded from environment variables and backend/.env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime settings for API, security, Snowflake, and conversion behavior."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ABAP to Snowflake Conversion Platform"
    environment: Literal["local", "dev", "stage", "prod"] = "local"
    log_level: str = "INFO"

    jwt_issuer: str = "abap-snowflake-platform"
    jwt_audience: str = "conversion-api"
    jwt_secret: SecretStr = Field(default=SecretStr("local-development-secret-change-me"))
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_conversion_topic: str = "abap.conversion.requests"
    kafka_validation_topic: str = "abap.validation.results"

    cortex_model_priority: list[str] = Field(
        default_factory=lambda: [
            "claude-4-sonnet",
            "openai-gpt-4.1",
            "llama3.3-70b",
        ]
    )
    confidence_threshold: float = 0.86
    max_remediation_retries: int = 3
    validation_sample_limit: int = 1000

    snowflake_account: str | None = Field(default=None, alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str | None = Field(default=None, alias="SNOWFLAKE_USER")
    snowflake_password: SecretStr | None = Field(default=None, alias="SNOWFLAKE_PASSWORD")
    snowflake_warehouse: str | None = Field(default=None, alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str | None = Field(default=None, alias="SNOWFLAKE_DATABASE")
    snowflake_schema: str | None = Field(default=None, alias="SNOWFLAKE_SCHEMA")
    snowflake_role: str | None = Field(default=None, alias="SNOWFLAKE_ROLE")
    snowflake_stage: str = "CONVERSION_ARTIFACTS"
    snowflake_disable_proxy: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so dependency injection reuses one configuration object."""
    return Settings()
