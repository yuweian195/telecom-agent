"""Application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TelecomAgent"
    version: str = "0.1.0"

    database_path: Path = BASE_DIR / "data" / "telecom_agent.db"
    alarms_csv: Path = BASE_DIR / "data" / "alarms" / "incident_day.csv"
    topology_path: Path = BASE_DIR / "data" / "topology" / "network.json"
    cases_path: Path = BASE_DIR / "data" / "cases" / "cases.jsonl"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout: float = 40.0

    window_minutes: int = 10
    confidence_threshold: float = 0.6

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
