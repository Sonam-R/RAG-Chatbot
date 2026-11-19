from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"          # ignored by Ollama, but the SDK requires a value
    chat_model: str = "llama3.1:8b"
    embed_model: str = "nomic-embed-text"
    allowed_origins: list[str] = ["http://localhost:3000"]
    # New fields for optional OpenAI/Ollama switch
    openai_api_key: str = ""
    use_ollama: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    # RAG‑specific configuration
    chroma_path: str = "./chroma_data"
    max_upload_mb: int = 10
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()