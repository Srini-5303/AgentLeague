"""Central, env-driven configuration for the Eldervale RPG.

Everything that differs between local and Azure runtimes is expressed here so the
rest of the codebase never reads os.environ directly. `shared/factory.py` consumes
this to wire up the right implementations behind each interface (the "seam").
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Runtime = Literal["local", "azure"]
LLMProvider = Literal["mock", "openai", "azure_openai", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    runtime: Runtime = "local"

    # LLM
    llm_provider: LLMProvider = "mock"
    character_model: str = "gpt-4o-mini"
    narrator_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1"

    # Game tuning
    agent_timeout_seconds: float = 5.0
    max_agents_per_turn: int = 4
    history_summarize_every: int = 10
    dice_seed: int | None = None

    # Local stores
    sqlite_path: str = ".data/eldervale.db"
    knowledge_dir: str = "knowledge"

    # Auth (local)
    dev_auth_secret: str = "dev-only-secret-change-me"
    dev_auth_bypass: bool = True
    dev_user_id: str = "dev-user-0001"

    # Azure runtime
    foundry_project_endpoint: str = ""
    character_agent_ids: str = ""  # JSON map {"warrior": "...", ...}
    narrator_agent_id: str = ""
    foundry_iq_index: str = "eldervale-campaign"
    cosmos_db_endpoint: str = ""
    cosmos_db_database: str = "fantasy-rpg"
    cosmos_users_container: str = "users"
    cosmos_sessions_container: str = "sessions"
    applicationinsights_connection_string: str = ""
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_user_id_claim: str = "sub"

    @field_validator("dice_seed", mode="before")
    @classmethod
    def _empty_seed_is_none(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v

    @property
    def character_agent_id_map(self) -> dict[str, str]:
        if not self.character_agent_ids:
            return {}
        return json.loads(self.character_agent_ids)


@lru_cache
def get_settings() -> Settings:
    return Settings()
