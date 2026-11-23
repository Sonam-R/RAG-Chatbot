from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.core.config import settings
from app.db.session import Base, engine
from app.db import models  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RAG Chatbot",
    description="FastAPI backend that streams OpenAI responses.",
    version="0.1.0",
)

# CORS configuration – allow requests from the Next.js dev server (port 3000/3001) and any origin during development
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # configurable via ALLOWED_ORIGINS in .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers (prefix /api is already set in each router module)
from app.api.documents import router as documents_router
app.include_router(chat_router)
app.include_router(documents_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
