from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    lti_consumer_key: str = Field(alias="LTI_CONSUMER_KEY")
    lti_consumer_secret: str = Field(alias="LTI_CONSUMER_SECRET")
    max_file_size_bytes: int = Field(default=20 * 1024 * 1024, alias="MAX_FILE_SIZE_BYTES")
    lti_timestamp_tolerance_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
