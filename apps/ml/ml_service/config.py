from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_URL")
    ollama_model: str = Field(default="qwen3:4b-instruct-2507-q4_K_M", alias="OLLAMA_MODEL")
    ml_token: str = Field(default="", alias="ML_TOKEN")
    ollama_timeout_seconds: float = Field(default=180, gt=0, le=1800, alias="ML_MODEL_TIMEOUT_SECONDS")
    queue_timeout_seconds: float = Field(default=5, gt=0, le=60, alias="ML_QUEUE_TIMEOUT_SECONDS")
    upload_timeout_seconds: float = Field(default=120, gt=0, le=600, alias="ML_UPLOAD_TIMEOUT_SECONDS")
    extraction_timeout_seconds: float = Field(default=20, gt=0, le=120, alias="ML_EXTRACTION_TIMEOUT_SECONDS")
    max_file_bytes: int = Field(default=20 * 1024 * 1024, gt=0, le=20 * 1024 * 1024, alias="ML_MAX_FILE_BYTES")
    max_request_bytes: int = Field(default=101 * 1024 * 1024, gt=0, le=110 * 1024 * 1024, alias="ML_MAX_REQUEST_BYTES")
    max_document_chars: int = Field(default=200_000, gt=0, le=1_000_000, alias="ML_MAX_DOCUMENT_CHARS")
    max_pages: int = Field(default=100, gt=0, le=1000, alias="ML_MAX_PAGES")
    max_docx_uncompressed_bytes: int = Field(default=32 * 1024 * 1024, gt=0, alias="ML_MAX_DOCX_UNCOMPRESSED_BYTES")
    context_tokens: int = Field(default=8192, ge=4096, le=32768, alias="ML_CONTEXT_TOKENS")
    output_tokens: int = Field(default=2048, ge=256, le=8192, alias="ML_OUTPUT_TOKENS")
    context_margin_tokens: int = Field(default=512, ge=256, alias="ML_CONTEXT_MARGIN_TOKENS")
    tokenizer_path: Path | None = Field(default=None, alias="ML_TOKENIZER_PATH")
    max_response_bytes: int = Field(default=512 * 1024, ge=1024, le=2 * 1024 * 1024, alias="ML_MAX_RESPONSE_BYTES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @field_validator("tokenizer_path", mode="before")
    @classmethod
    def empty_tokenizer_path(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_budget(self):
        if self.output_tokens + self.context_margin_tokens >= self.context_tokens:
            raise ValueError("Output reserve must be smaller than the context window")
        if not self.ollama_url.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_URL must be an HTTP(S) address")
        return self
