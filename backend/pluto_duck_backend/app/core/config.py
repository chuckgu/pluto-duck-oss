"""Centralized configuration management for Pluto-Duck."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATA_ROOT = Path.home() / ".pluto-duck"


class DuckDBSettings(BaseModel):
    """Settings related to the embedded DuckDB warehouse."""

    path: Path = Field(default_factory=lambda: DEFAULT_DATA_ROOT / "data" / "warehouse.duckdb")
    threads: int = Field(default=4, ge=1, description="Number of DuckDB threads to use")


class DbtSettings(BaseModel):
    """Configuration for the bundled dbt project."""

    project_path: Path = Field(default_factory=lambda: DEFAULT_DATA_ROOT / "dbt")
    profiles_path: Optional[Path] = None


class AgentSettings(BaseModel):
    """LLM provider and agent-specific configuration."""

    provider: str = Field(default="openai", description="LLM provider identifier")
    model: str = Field(default="gpt-4.1-mini", description="Default model name")
    api_base: Optional[HttpUrl] = Field(default=None, description="Override base URL for provider")
    api_key: Optional[str] = Field(default=None, description="API key for the LLM provider")
    mock_mode: bool = Field(default=False, description="Use local mock responses instead of live LLM")


class DataDirectory(BaseModel):
    """Directory layout for Pluto-Duck artifacts."""

    root: Path = Field(default_factory=lambda: DEFAULT_DATA_ROOT)
    artifacts: Path = Field(default_factory=lambda: DEFAULT_DATA_ROOT / "artifacts")
    configs: Path = Field(default_factory=lambda: DEFAULT_DATA_ROOT / "configs")

    def ensure(self) -> None:
        """Create the necessary directories if they don't exist."""

        for directory in {self.root, self.artifacts, self.configs}:
            directory.mkdir(parents=True, exist_ok=True)


class PlutoDuckSettings(BaseSettings):
    """Application-wide settings loaded from env, .env, and defaults."""

    data_dir: DataDirectory = Field(default_factory=DataDirectory)
    duckdb: DuckDBSettings = Field(default_factory=DuckDBSettings)
    dbt: DbtSettings = Field(default_factory=DbtSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    log_level: str = Field(default="INFO", description="Log verbosity")
    enable_telemetry: bool = Field(default=False, description="Send anonymous usage metrics")

    model_config = SettingsConfigDict(
        env_prefix="PLUTODUCK_",
        env_file=".env",
        extra="ignore",
        env_nested_delimiter="__",
    )

    def prepare_environment(self) -> None:
        """Ensure directories exist and derive dependent settings."""

        root_override = os.getenv("PLUTODUCK_DATA_DIR__ROOT")
        if root_override:
            self.data_dir.root = Path(root_override)

        agent_provider_override = os.getenv("PLUTODUCK_AGENT__PROVIDER")
        if agent_provider_override:
            self.agent.provider = agent_provider_override

        self.data_dir.ensure()
        # Fill derived paths if not explicitly provided
        if self.dbt.project_path == DEFAULT_DATA_ROOT / "dbt":
            self.dbt.project_path = self.data_dir.root / "dbt"
        if self.dbt.profiles_path is None:
            self.dbt.profiles_path = self.data_dir.configs / "dbt_profiles"


@lru_cache(maxsize=1)
def get_settings() -> PlutoDuckSettings:
    """Return a cached settings instance."""

    settings = PlutoDuckSettings()
    settings.prepare_environment()
    return settings


