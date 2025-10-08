from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
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
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/tactyo"
    )
    session_secret: str = Field(default="change-me", min_length=16)
    encryption_key: str = Field(
        default="",
        description="Chave base64 (32 bytes) usada para criptografar segredos",
    )
    webhook_secret: str = Field(
        default="",
        description="Secret para validar webhooks do GitHub (HMAC SHA-256)",
    )
    cors_origins: List[str] = Field(
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
    def parse_cors_origins(cls, value) -> List[str]:
        """Parse CORS origins from string or list.

        Aceita:
        - None ou string vazia -> retorna lista padrão
        - String separada por vírgulas -> converte para lista
        - Lista -> retorna como está
        """
        # Se for None, string vazia, ou "null"
        if value is None or value == "" or value == "null":
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]

        # Se for string, divide por vírgula
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            return origins if origins else [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]

        # Se já for lista, retorna como está
        if isinstance(value, list):
            return value

        # Fallback para lista padrão
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    @field_validator("encryption_key", mode="after")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        if not value:
            raise ValueError("TACTYO_ENCRYPTION_KEY é obrigatório")
        import base64

        # Tenta base64 URL-safe primeiro (usado por Fernet), depois base64 padrão
        try:
            key_bytes = base64.urlsafe_b64decode(value)
        except Exception:
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

        # Tenta URL-safe primeiro (Fernet), depois padrão
        try:
            return base64.urlsafe_b64decode(self.encryption_key)
        except Exception:
            return base64.b64decode(self.encryption_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
