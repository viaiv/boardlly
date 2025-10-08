import os
from functools import lru_cache
from typing import Any, List, Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TACTYO_",
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customiza sources para mapear TACTYO_CORS_ORIGINS para cors_origins_str."""

        # Cria uma custom source que mapeia TACTYO_CORS_ORIGINS
        class CorsOriginsMappingSource(PydanticBaseSettingsSource):
            def get_field_value(self, field_name: str, field_info: Any) -> Tuple[Any, str, bool]:
                if field_name == "cors_origins_str":
                    # Procura por TACTYO_CORS_ORIGINS primeiro
                    value = os.environ.get("TACTYO_CORS_ORIGINS")
                    if value is not None:
                        return value, "cors_origins", True
                return None, "", False

            def __call__(self) -> dict[str, Any]:
                d: dict[str, Any] = {}
                for field_name in self.settings_cls.model_fields:
                    field_value, field_key, value_is_complex = self.get_field_value(
                        field_name, self.settings_cls.model_fields[field_name]
                    )
                    if field_key:
                        d[field_name] = field_value
                return d

        return (
            init_settings,
            CorsOriginsMappingSource(settings_cls),
            env_settings,
            dotenv_settings,
            file_secret_settings,
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
    # CORS origins como string para evitar parse automático de JSON
    # Use TACTYO_CORS_ORIGINS para definir (aceita string separada por vírgulas)
    # A property cors_origins retorna como lista
    # Mapeamento de TACTYO_CORS_ORIGINS para cors_origins_str é feito no custom settings source
    cors_origins_str: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )
    enable_cors: bool = Field(default=True)

    docs_url: str | None = "/docs"
    openapi_url: str = "/openapi.json"
    session_cookie_name: str = Field(default="tactyo_session")
    session_max_age_seconds: int = Field(default=60 * 60 * 24 * 7)

    # SMTP Configuration
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="noreply@tactyo.com")
    smtp_from_name: str = Field(default="Tactyo")
    smtp_use_tls: bool = Field(default=True)

    # Frontend URL for email links
    frontend_url: str = Field(default="http://localhost:5173")

    @property
    def cors_origins(self) -> List[str]:
        """Retorna CORS origins como lista de strings."""
        value = self.cors_origins_str
        # Se for string vazia ou "null", retorna lista padrão
        if not value or value == "null":
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        # Divide por vírgula e remove espaços
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        # Se resultou em lista vazia, retorna padrão
        return origins if origins else [
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
