"""Application settings loaded from environment variables or .env file."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the NeuralScope backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NEURALSCOPE_",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    hf_cache_dir: Path = Path.home() / ".cache" / "huggingface"
    gpu_stats_interval_seconds: float = 2.0
    max_upload_size_mb: int = 100


settings = Settings()
