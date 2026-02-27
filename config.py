import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APPLE_AI_",
        env_file=".env",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: Optional[int] = None  # If None, will auto-find available port
    max_concurrency: int = Field(default=4, ge=1, le=128)
    request_timeout: float = Field(default=30.0, gt=0.0, le=60.0)
    api_key: Optional[str] = None
    
    @property
    def is_port_fixed(self) -> bool:
        """Return True if port is explicitly set via env."""
        return self.port is not None
