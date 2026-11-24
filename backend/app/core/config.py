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
    # Groq configuration (primary LLM provider)
    # ------------------------------------------------------------
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: str = ""   # populated from GROQ_API_KEY env variable (do not commit secrets)
    groq_chat_model: str = "gemma2-9b-it"

    # ------------------------------------------------------------
    # RAG‑specific configuration values.
    # ------------------------------------------------------------
    # Directory where ChromaDB will persist its vector collection.
    chroma_path: str = "./chroma_data"
    # Maximum size (in megabytes) allowed for a single uploaded document.
    max_upload_mb: int = 10
    # Desired size (in tokens) of each text chunk before embedding.
    chunk_size: int = 500
    # Number of tokens to overlap between consecutive chunks to preserve context.
    chunk_overlap: int = 50
    # How many nearest‑neighbor chunks to retrieve when answering a query.
    top_k: int = 5
    # Drop retrieved chunks whose cosine similarity is below this; 0.5 is a placeholder — tune from /search scores.
    min_score: float = 0.5
    # How many recent conversation turns to include when rewriting follow-up questions into standalone queries.
    rewrite_history_turns: int = 4
    # Chat-model temperature; keep low so answers stay focused on retrieved context.
    chat_temperature: float = 0.2
    # How long Ollama keeps models loaded after a request (e.g. 30m, -1).
    ollama_keep_alive: str = "30m"
    # Optional smaller model for query rewriting; None uses CHAT_MODEL.
    rewriter_model: str | None = None
    # Chunks included in the RAG prompt (after min_score filter; search still uses TOP_K).
    rag_top_k: int = 3
    # Recent messages sent to the chat model when use_documents is true.
    chat_history_limit: int = 8
    rate_limit_chat: str = "20/minute"
    rate_limit_upload: str = "5/minute"
    rate_limit_default: str = "60/minute"
    max_chunks_per_document: int = 500
    llm_timeout_seconds: float = 120.0
    embed_timeout_seconds: float = 30.0

    # Tell pydantic to read values from a .env file at the project root.
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
