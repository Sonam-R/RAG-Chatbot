import json
import logging
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from ..core.config import settings
from ..llm.provider import stream_chat
from ..rag.embedder import embed_texts
from ..rag.vector_store import search as vector_search
from ..db.session import SessionLocal
from ..db.models import Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

async def build_context(question: str) -> str:
    """Return a system prompt with the most relevant uploaded-document chunks.
    Returns an empty string if nothing is found or retrieval fails, so chat still works.
    """
    try:
        query_emb = (await embed_texts([question], prefix="search_query: "))[0]
        hits = await run_in_threadpool(vector_search, query_emb, settings.top_k)
    except Exception:
        logger.exception("Retrieval failed; answering without document context")
        return ""
    if not hits:
        return ""
    excerpts = "\n\n".join(
        f"[{h['filename']}, page {h['page']}]\n{h['text']}" for h in hits
    )
    return (
        "Use the following excerpts from the user's uploaded documents when they are "
        "relevant to the question, and mention the file name and page you used. "
        "If they are not relevant, ignore them.\n\n" + excerpts
    )

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@router.post("/chat")
async def chat(req: ChatRequest):
    db = SessionLocal()
    try:
        # Retrieve existing conversation or create a new one
        if req.conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
            if not conv:
                conv = Conversation(id=req.conversation_id)
                db.add(conv)
                db.commit()
                db.refresh(conv)
        else:
            conv = Conversation()
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # Store the user's message
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=req.message,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Gather full conversation history for the LLM
        history = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id)
            .all()
        )
        messages_for_llm = [{"role": m.role, "content": m.content} for m in history]

        # Add relevant document excerpts (if any) as extra context for this turn only
        context = await build_context(req.message)
        if context:
            messages_for_llm.insert(0, {"role": "system", "content": context})

        async def event_stream():
            # First send the conversation ID so the client can keep track
            yield f"data: {json.dumps({'conversation_id': conv.id})}\n\n"
            try:
                async for token in stream_chat(messages_for_llm):
                    yield f"data: {json.dumps({'token': token})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception:
                yield f"data: {json.dumps({'error': 'Something went wrong'})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    finally:
        db.close()
