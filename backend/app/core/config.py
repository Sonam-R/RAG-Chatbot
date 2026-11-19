"""Application configuration using Pydantic Settings.

This file loads environment variables from a .env file located in the backend root.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    chat_model: str = "gpt-4o-mini"
    use_ollama: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
