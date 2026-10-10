from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SPECTRA"
    app_env: str = "development"
    api_v1_prefix: str = "/api"
    serpapi_api_key: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_fallback_models: str = "gpt-4.1-mini,gpt-4o-mini"
    llm_base_url: str = ""
    llm_timeout_seconds: float = 45.0
    cors_origins: str = "http://localhost:3000"
    serpapi_timeout_seconds: float = 30.0
    serpapi_max_retries: int = 2
    serpapi_cache_ttl_seconds: float = 900.0
    runs_dir: str = "backend/data/runs"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), env_file_encoding="utf-8", extra="ignore")

    @field_validator("serpapi_timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: float) -> float:
        if not 1.0 <= value <= 120.0:
            raise ValueError("SERPAPI_TIMEOUT_SECONDS must be between 1 and 120 seconds")
        return value

    @field_validator("serpapi_max_retries")
    @classmethod
    def validate_retries(cls, value: int) -> int:
        if not 0 <= value <= 3:
            raise ValueError("SERPAPI_MAX_RETRIES must be between 0 and 3")
        return value

    @property
    def llm_model_chain(self) -> list[str]:
        chain = [self.llm_model] + [m.strip() for m in self.llm_fallback_models.split(",") if m.strip()]
        return list(dict.fromkeys(m for m in chain if m))

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
