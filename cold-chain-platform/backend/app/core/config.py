from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://cold_chain:cold_chain@localhost:5432/cold_chain"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-before-production"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    amap_key: str = ""
    amap_security_code: str = ""
    backup_dir: str = "backups"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env.lower() in {"prod", "production"} and self.jwt_secret in {
            "change-me-before-production",
            "please-change-me",
            "",
        }:
            raise ValueError("JWT_SECRET must be changed before production startup")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
