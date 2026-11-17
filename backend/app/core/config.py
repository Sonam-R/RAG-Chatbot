"""Application configuration using Pydantic Settings.

This file loads environment variables from a .env file located in the backend root.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    chat_model: str = "gpt-4o-mini"
    allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
