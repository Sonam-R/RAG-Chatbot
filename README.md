# RAG Chatbot

FastAPI + Next.js retrieval-augmented chatbot over local Ollama embeddings and generation.

See `backend/` and `frontend/` for setup. Evaluation lives under `eval/`.

## Known limitations

There is no authentication yet: every user can list, query, and delete every uploaded document. The app is not suitable for private or sensitive files. Rate limiting is applied per client IP only, so it is a light abuse deterrent rather than strong multi-tenant protection.