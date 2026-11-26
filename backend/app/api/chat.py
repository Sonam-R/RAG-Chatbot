import json
import logging
import re
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.chat_metrics import ChatRequestMetrics
from app.core.config import settings
from app.core.errors import MODEL_UNAVAILABLE_MESSAGE, ModelUnavailableError, map_openai_error
from app.core.limiter import limiter
from app.core.logging import log_chat_audit
from app.core.request_context import get_request_id
from app.db.models import Conversation, Message
from app.db.session import SessionLocal
from app.rag.embedder import embed_texts
from app.rag.prompt import NOT_FOUND_MESSAGE, build_messages
from app.rag.rewriter import rewrite_question
from app.rag.vector_store import search as vector_search
from app.llm.provider import client, stream_chat
from app.graph.builder import rag_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
_QUERY_PREFIX = "search_query: "


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    use_documents: bool = True


class MessageOut(BaseModel):
    role: str
    content: str
    sources: list[dict] | None = None


class ConversationOut(BaseModel):
    id: str
    title: str
    messages: list[MessageOut]


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


def _parse_sources(raw: str | None) -> list[dict] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        logger.warning("Failed to parse stored sources JSON")
        return None
    logger.warning("Stored sources is not a JSON list")
    return None


def _save_assistant(conv_id: str, text: str, sources: list[dict] | None = None) -> None:
    if not text:
        return
    db = SessionLocal()
    try:
        stored = json.dumps(sources) if sources else None
        db.add(
            Message(
                conversation_id=conv_id,
                role="assistant",
                content=text,
                sources=stored,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to save assistant message")
    finally:
        db.close()


def _chunk_summaries(hits: list[dict]) -> list[dict]:
    return [{"chunk_id": h.get("chunk_id"), "score": h.get("score")} for h in hits]


async def retrieve_chunks(
    question: str, history: list[dict], metrics: ChatRequestMetrics
) -> list[dict] | None:
    """Rewrite, embed, search, and drop hits below min_score. None means retrieval failed."""
    try:
        t0 = time.perf_counter()
        rewritten = await run_in_threadpool(rewrite_question, question, history)
        metrics.rewrite_s = round(time.perf_counter() - t0, 4)
        metrics.rewritten_question = rewritten

        t0 = time.perf_counter()
        query_emb = (await embed_texts([rewritten], prefix=_QUERY_PREFIX))[0]
        metrics.embed_s = round(time.perf_counter() - t0, 4)

        t0 = time.perf_counter()
        hits = await run_in_threadpool(vector_search, query_emb, settings.top_k)
        metrics.search_s = round(time.perf_counter() - t0, 4)
        metrics.chunks_before = _chunk_summaries(hits)

        filtered = [h for h in hits if (h.get("score") or 0) >= settings.min_score]
        metrics.chunks_after = _chunk_summaries(filtered)
        return filtered[: settings.rag_top_k]
    except ModelUnavailableError:
        raise
    except Exception:
        logger.warning("Document retrieval failed; answering without documents", exc_info=True)
        return None


async def _stream_llm(messages: list[dict], temperature: float | None = None):
    kwargs: dict = {
        "model": settings.chat_model,
        "messages": messages,
        "stream": True,
        "extra_body": {"keep_alive": settings.ollama_keep_alive},
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    try:
        stream = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        try:
            map_openai_error(exc)
        except ModelUnavailableError:
            raise
        raise
    try:
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        try:
            map_openai_error(exc)
        except ModelUnavailableError:
            raise
        raise


def _record_first_token(request_start: float, ttft_state: dict[str, float | None]) -> None:
    if ttft_state["t"] is None:
        ttft_state["t"] = time.perf_counter() - request_start


def _emit_audit(metrics: ChatRequestMetrics) -> None:
    log_chat_audit(metrics.to_log_dict(get_request_id()))


def _sse_data(payload: object) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _unwrap_custom_event(event: object) -> dict | None:
    """LangGraph custom stream may yield a dict or (namespace, dict) tuples."""
    if isinstance(event, dict):
        return event
    if isinstance(event, (list, tuple)) and len(event) == 2:
        _ns, data = event
        if isinstance(data, dict):
            return data
    return None


@router.post("/chat")
@limiter.limit(settings.rate_limit_chat)
async def chat(request: Request, req: ChatRequest):
    db = SessionLocal()
    try:
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

        user_msg = Message(conversation_id=conv.id, role="user", content=req.message)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        history = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id)
            .all()
        )
        messages_for_llm = [{"role": m.role, "content": m.content} for m in history]
        prior_history = messages_for_llm[:-1]
        conv_id = str(conv.id)
        use_documents = req.use_documents
        question = req.message
        history_for_graph = [
            {"role": m["role"], "content": m["content"]} for m in prior_history
        ]

        metrics = ChatRequestMetrics(
            conversation_id=conv_id,
            use_documents=use_documents,
            question_chars=len(question),
        )
    finally:
        db.close()

    async def event_stream():
        state: dict = {
            "request_id": get_request_id(),
            "question": question,
            "history": history_for_graph,
            "use_documents": use_documents,
            "retries": 0,
        }
        yield _sse_data({"conversation_id": conv_id})

        answer_parts: list[str] = []
        final_sources: list[dict] | None = None

        try:
            async for raw in rag_graph.astream(state, stream_mode="custom"):
                event = _unwrap_custom_event(raw)
                if not event:
                    continue
                if "token" in event:
                    answer_parts.append(event["token"])
                    yield _sse_data({"token": event["token"]})
                elif "sources" in event:
                    final_sources = event["sources"]
                    yield _sse_data({"sources": final_sources})
                elif "status" in event:
                    yield _sse_data({"status": event["status"]})
                elif "verification" in event:
                    yield _sse_data({"verification": event["verification"]})
                elif "error" in event:
                    raise RuntimeError(event["error"])
        except Exception:
            logger.exception("Graph execution failed")
            yield _sse_data({"error": "Something went wrong"})
        finally:
            answer_text = "".join(answer_parts)
            _save_assistant(conv_id, answer_text, final_sources)
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
@limiter.limit(settings.rate_limit_default)
def get_conversation(request: Request, conversation_id: str):
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        rows = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id)
            .all()
        )
        return ConversationOut(
            id=conv.id,
            title=conv.title,
            messages=[
                MessageOut(
                    role=m.role,
                    content=m.content,
                    sources=_parse_sources(m.sources),
                )
                for m in rows
            ],
        )
    finally:
        db.close()