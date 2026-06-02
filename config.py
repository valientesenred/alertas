from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/alertas_db"

    # WhatsApp Cloud API
    WA_PHONE_NUMBER_ID: str = ""
    WA_ACCESS_TOKEN: str = ""
    WA_VERIFY_TOKEN: str = "token_verificacion_secreto"
    WA_API_VERSION: str = "v19.0"

    # Seguridad
    SECRET_KEY: str = "cambia_esto_en_produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # URL base de la plataforma (para mini web de ubicación)
    BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"

    # Módulo
    MODULE_PREFIX: str = "/alertas"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
