import json
import logging
import re
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from ..core.config import settings
from ..llm.provider import client, stream_chat
from ..rag.embedder import embed_texts
from ..rag.prompt import NOT_FOUND_MESSAGE, build_messages
from ..rag.rewriter import rewrite_question
from ..rag.vector_store import search as vector_search
from ..db.session import SessionLocal
from ..db.models import Conversation, Message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Same query-side prefix the search endpoint passes to embed_texts.
_QUERY_PREFIX = "search_query: "


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    use_documents: bool = True


def _snippet(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) > 200:
        return collapsed[:200] + "..."
    return collapsed


def _sources_payload(chunks: list[dict]) -> dict:
    return {
        "sources": [
            {
                "n": i,
                "filename": c.get("filename"),
                "page": c.get("page"),
                "snippet": _snippet(c.get("text") or ""),
                "score": round(float(c.get("score") or 0), 3),
            }
            for i, c in enumerate(chunks, start=1)
        ]
    }


def _save_assistant(conv_id: str, text: str) -> None:
    if not text:
        return
    db = SessionLocal()
    try:
        db.add(Message(conversation_id=conv_id, role="assistant", content=text))
        db.commit()
    except Exception:
        logger.exception("Failed to save assistant message")
    finally:
        db.close()


async def retrieve_chunks(question: str, history: list[dict]) -> list[dict] | None:
    """Rewrite, embed, search, and drop hits below min_score. None means retrieval failed."""
    try:
        rewritten = await run_in_threadpool(rewrite_question, question, history)
        query_emb = (await embed_texts([rewritten], prefix=_QUERY_PREFIX))[0]
        hits = await run_in_threadpool(vector_search, query_emb, 5)
        return [h for h in hits if (h.get("score") or 0) >= settings.min_score]
    except Exception:
        logger.warning("Document retrieval failed; answering without documents")
        return None


async def _stream_llm(messages: list[dict], temperature: float | None = None):
    kwargs: dict = {
        "model": settings.chat_model,
        "messages": messages,
        "stream": True,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


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
        prior_history = messages_for_llm[:-1]
        conv_id = conv.id
        use_documents = req.use_documents

        async def event_stream():
            yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"

            chunks: list[dict] | None = None
            if use_documents:
                chunks = await retrieve_chunks(req.message, prior_history)
                if chunks is not None and not chunks:
                    logger.info("No relevant document chunks; skipping LLM")
                    yield f"data: {json.dumps({'token': NOT_FOUND_MESSAGE})}\n\n"
                    _save_assistant(conv_id, NOT_FOUND_MESSAGE)
                    yield f"data: {json.dumps({'sources': []})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

            if use_documents and chunks:
                llm_messages = build_messages(req.message, chunks, prior_history)
                parts: list[str] = []
                try:
                    async for token in _stream_llm(llm_messages, settings.chat_temperature):
                        parts.append(token)
                        yield f"data: {json.dumps({'token': token})}\n\n"
                except Exception:
                    logger.exception("Chat generation failed")
                    yield f"data: {json.dumps({'error': 'Something went wrong'})}\n\n"
                    return
                _save_assistant(conv_id, "".join(parts))
                yield f"data: {json.dumps(_sources_payload(chunks))}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Day 2 path: no rewriting, no search, no sources event
            parts: list[str] = []
            try:
                async for token in stream_chat(messages_for_llm):
                    parts.append(token)
                    yield f"data: {json.dumps({'token': token})}\n\n"
            except Exception:
                logger.exception("Chat generation failed")
                yield f"data: {json.dumps({'error': 'Something went wrong'})}\n\n"
                return
            _save_assistant(conv_id, "".join(parts))
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    finally:
        db.close()
