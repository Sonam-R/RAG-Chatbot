import json, logging, time
from typing import List, Dict, Any

from langgraph.config import get_stream_writer

from app.core.config import settings
from app.core.errors import ModelUnavailableError
from app.rag.rewriter import rewrite_question
from app.rag.embedder import embed_texts
from app.rag.vector_store import search as vector_search
from app.rag.prompt import NOT_FOUND_MESSAGE, build_messages, format_context
from app.llm.provider import stream_chat

logger = logging.getLogger(__name__)

# Helper to write custom SSE events
def _write_event(payload: dict) -> None:
    writer = get_stream_writer()
    writer(json.dumps(payload))

# ----------------------------------------------------------------------
# Node: plain_chat (use_documents=False)
# ----------------------------------------------------------------------
async def plain_chat(state: Dict[str, Any]) -> Dict[str, Any]:
    # Build a simple chat without retrieval.
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        *state.get("history", [])[-settings.chat_history_limit :],
        {"role": "user", "content": state["question"]},
    ]
    async for token in stream_chat(messages):
        _write_event({"token": token})
    _write_event({"sources": []})
    return state

# ----------------------------------------------------------------------
# Node: rewrite
# ----------------------------------------------------------------------
async def rewrite(state: Dict[str, Any]) -> Dict[str, Any]:
    if not state.get("history"):
        state["standalone"] = state["question"]
        return state
    try:
        rewritten = await rewrite_question(state["question"], state["history"])
        state["standalone"] = rewritten
    except Exception as exc:
        logger.warning("Rewrite failed, falling back to original", exc_info=True)
        state["standalone"] = state["question"]
    return state

# ----------------------------------------------------------------------
# Node: retrieve
# ----------------------------------------------------------------------
async def retrieve(state: Dict[str, Any]) -> Dict[str, Any]:
    _write_event({"status": "searching documents..."})
    # embed with prefix
    query_emb = (await embed_texts([state["standalone"]], prefix="search_query: "))[0]
    hits = await vector_search(query_emb, settings.top_k)
    filtered = [h for h in hits if (h.get("score") or 0) >= settings.min_score]
    top_score = max((h.get("score", 0) for h in filtered), default=0.0)
    logger.info(
        "retrieve",
        extra={
            "request_id": state.get("request_id"),
            "hits": len(filtered),
            "top_score": top_score,
        },
    )
    state["hits"] = filtered[: settings.rag_top_k]
    if state["hits"]:
        state["context"] = format_context(state["hits"])
        state["sources"] = [
            {
                "n": i,
                "filename": c.get("filename"),
                "page": c.get("page"),
                "snippet": c.get("text", ""),
                "score": round(float(c.get("score") or 0), 3),
            }
            for i, c in enumerate(state["hits"], start=1)
        ]
    else:
        state["context"] = ""
        state["sources"] = []
    return state

# ----------------------------------------------------------------------
# Node: grade (Phase‑2 optional)
# ----------------------------------------------------------------------
async def grade(state: Dict[str, Any]) -> Dict[str, Any]:
    # Short yes/no relevance check.
    prompt = [
        {"role": "system", "content": "Answer ONLY with 'yes' or 'no'."},
        {
            "role": "user",
            "content": f"Question: {state['question']}\nContext: {state.get('context', '')}",
        },
    ]
    answer = ""
    try:
        async for token in stream_chat(prompt):
            answer += token.strip().lower()
    except Exception:
        logger.warning("Relevance grading failed – treating as relevant", exc_info=True)
        state["relevant"] = True
        return state
    state["relevant"] = "yes" in answer
    return state

# ----------------------------------------------------------------------
# Node: generate (normal RAG answer)
# ----------------------------------------------------------------------
async def generate(state: Dict[str, Any]) -> Dict[str, Any]:
    # Build full messages using existing helper.
    messages = build_messages(state["question"], state.get("hits", []), state.get("history", []))
    async for token in stream_chat(messages):
        _write_event({"token": token})
    _write_event({"sources": state.get("sources", [])})
    return state

# ----------------------------------------------------------------------
# Node: refuse (no hits)
# ----------------------------------------------------------------------
async def refuse(state: Dict[str, Any]) -> Dict[str, Any]:
    for ch in NOT_FOUND_MESSAGE:
        _write_event({"token": ch})
    _write_event({"sources": []})
    return state
