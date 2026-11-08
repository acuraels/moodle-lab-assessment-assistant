from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    lti_consumer_key: str = Field(alias="LTI_CONSUMER_KEY")
    lti_consumer_secret: str = Field(alias="LTI_CONSUMER_SECRET")
    max_file_size_bytes: int = Field(default=20 * 1024 * 1024, alias="MAX_FILE_SIZE_BYTES")
    ml_url: str = Field(default="", alias="ML_URL")
    ml_token: str = Field(default="", alias="ML_TOKEN", repr=False)
    ml_timeout_seconds: float = Field(default=540, gt=0, le=1800, alias="ML_TIMEOUT_SECONDS")
    ml_max_attempts: int = Field(default=2, ge=1, le=5, alias="ML_MAX_ATTEMPTS")
    ml_retry_delay_seconds: float = Field(default=10, ge=0, le=300, alias="ML_RETRY_DELAY_SECONDS")
    ml_processing_deadline_seconds: int = Field(default=1800, ge=1, le=86400, alias="ML_PROCESSING_DEADLINE_SECONDS")
    ml_poll_seconds: float = Field(default=2, gt=0, le=60, alias="ML_POLL_SECONDS")
    lti_timestamp_tolerance_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @field_validator("ml_url")
    @classmethod
    def validate_ml_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value:
            return value
        parts = urlsplit(value)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username or parts.password or parts.query or parts.fragment):
            raise ValueError("ML_URL must be an HTTP(S) service URL without credentials, query or fragment")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
