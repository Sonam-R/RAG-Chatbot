from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # URL for the local Ollama server (OpenAI‑compatible endpoint).
    llm_base_url: str = "http://localhost:11434/v1"
    # API key placeholder required by the OpenAI SDK; Ollama ignores it.
    llm_api_key: str = "ollama"          # ignored by Ollama, but the SDK requires a value
    # Name of the chat model used for generation.
    chat_model: str = "llama3.1:8b"
    # Name of the embedding model used to turn text chunks into vectors.
    embed_model: str = "nomic-embed-text"
    # Origins allowed to make CORS requests to the FastAPI server.
    allowed_origins: list[str] = ["http://localhost:3000"]

    # ------------------------------------------------------------
    # Optional switch between OpenAI and Ollama.
    # ------------------------------------------------------------
    # If you set an actual OpenAI key here, the provider will call the OpenAI API.
    openai_api_key: str = ""
    # When True, the code will talk to Ollama instead of OpenAI.
    use_ollama: bool = False
    # Base URL for Ollama when use_ollama is True.
    ollama_base_url: str = "http://127.0.0.1:11434/v1"

    # ------------------------------------------------------------
    # RAG‑specific configuration values.
    # ------------------------------------------------------------
    # Directory where ChromaDB will persist its vector collection.
    chroma_path: str = "./chroma_data"
    # Maximum size (in megabytes) allowed for a single uploaded document.
    max_upload_mb: int = 10
    # Desired size (in characters) of each text chunk before embedding.
    chunk_size: int = 500
    # Number of characters to overlap between consecutive chunks to preserve context.
    chunk_overlap: int = 50
    # How many nearest‑neighbor chunks to retrieve when answering a query.
    top_k: int = 5

    # Tell pydantic to read values from a .env file at the project root.
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
