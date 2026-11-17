from fastapi import FastAPI
from app.api.chat import router as chat_router

app = FastAPI(
    title="RAG Chatbot",
    description="FastAPI backend that streams OpenAI responses.",
    version="0.1.0",
)

# Include the chat router (prefix /api is already set in chat.py)
app.include_router(chat_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
