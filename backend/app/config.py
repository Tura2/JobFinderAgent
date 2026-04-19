from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    openrouter_api_key: str
    openrouter_model: str = "anthropic/claude-opus-4.5"

    # Pipeline
    match_threshold: int = 65
    scan_interval_hours: int = 4

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # App
    pwa_access_token: str
    pwa_base_url: str = "http://localhost:8000"

    # Database
    database_url: str = "sqlite:///./jobfinder.db"

    # Applicant info for ATS pre-fill (Amendment B)
    applicant_first_name: str = ""
    applicant_last_name: str = ""
    applicant_email: str = ""
    applicant_linkedin_url: str = ""
    applicant_portfolio_url: str = ""

    @field_validator("match_threshold")
    @classmethod
    def threshold_in_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("match_threshold must be between 0 and 100")
        return v


settings = Settings()
