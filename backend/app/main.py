from fastapi import FastAPI
from app.api.chat import router as chat_router
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
    allow_origins=["*"],  # you can restrict to "http://localhost:3000", "http://localhost:3001" if desired
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the chat router (prefix /api is already set in chat.py)
from app.api.documents import router as documents_router
app.include_router(documents_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
