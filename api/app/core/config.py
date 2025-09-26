from functools import lru_cache
from typing import List

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TACTYO_",
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Tactyo API"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    database_url: AnyUrl | str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/tactyo"
    )
    session_secret: str = Field(default="change-me", min_length=16)
    encryption_key: str = Field(
        default="",
        description="Chave base64 (32 bytes) usada para criptografar segredos",
    )
    cors_origins: List[AnyUrl | str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    enable_cors: bool = Field(default=True)

    docs_url: str | None = "/docs"
    openapi_url: str = "/openapi.json"
    session_cookie_name: str = Field(default="tactyo_session")
    session_max_age_seconds: int = Field(default=60 * 60 * 24 * 7)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, value: str | List[AnyUrl | str]) -> List[AnyUrl | str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("encryption_key", mode="after")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        if not value:
            raise ValueError("TACTYO_ENCRYPTION_KEY é obrigatório")
        import base64

        try:
            key_bytes = base64.b64decode(value)
        except Exception as exc:  # pragma: no cover - validation error details
            raise ValueError("TACTYO_ENCRYPTION_KEY inválida: não é base64 válido") from exc
        if len(key_bytes) != 32:
            raise ValueError("TACTYO_ENCRYPTION_KEY deve decodificar para 32 bytes")
        return value

    @property
    def encryption_key_bytes(self) -> bytes:
        import base64

        return base64.b64decode(self.encryption_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
