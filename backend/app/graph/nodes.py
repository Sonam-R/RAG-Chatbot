import logging
from typing import Dict, Any

from langgraph.config import get_stream_writer

from app.core.config import settings
from app.rag.rewriter import rewrite_question
from app.rag.embedder import embed_texts
from app.rag.vector_store import search as vector_search
from app.rag.prompt import NOT_FOUND_MESSAGE, build_messages, format_context
from app.llm.provider import stream_chat
from app.graph import guards

logger = logging.getLogger(__name__)


def _write_event(payload: dict) -> None:
    writer = get_stream_writer()
    writer(payload)


# ----------------------------------------------------------------------
# Node: input_guard (optional; no-op pass-through when disabled is handled in builder)
# ----------------------------------------------------------------------
async def input_guard(state: Dict[str, Any]) -> Dict[str, Any]:
    # Speed bump only — not real security; do not treat as robust filtering.
    normalized = guards.normalize_question(state["question"])
    state["question"] = normalized

    pattern_name = guards.detect_injection(normalized)
    if pattern_name is None:
        state["input_blocked"] = False
        return state

    state["input_blocked"] = True
    state["block_reason"] = pattern_name
    logger.info(
        "input_blocked",
        extra={"request_id": state.get("request_id"), "reason": pattern_name},
    )
    for ch in guards.BLOCKED_MESSAGE:
        _write_event({"token": ch})
    _write_event({"sources": []})
    _write_event({"status": "blocked"})
    return state


# ----------------------------------------------------------------------
# Node: plain_chat (use_documents=False)
# ----------------------------------------------------------------------
async def plain_chat(state: Dict[str, Any]) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        *state.get("history", [])[-settings.chat_history_limit :],
        {"role": "user", "content": state["question"]},
    ]
    parts: list[str] = []
    async for token in stream_chat(messages):
        parts.append(token)
        _write_event({"token": token})
    state["answer"] = "".join(parts)
    _write_event({"sources": []})
    return state


# ----------------------------------------------------------------------
# Node: rewrite
# ----------------------------------------------------------------------
async def rewrite(state: Dict[str, Any]) -> Dict[str, Any]:
    retries = state.get("retries", 0)
    if retries > 0:
        # Broader retry: use the original question as the retrieval query.
        state["standalone"] = state["question"]
        return state
    if not state.get("history"):
        state["standalone"] = state["question"]
        return state
    try:
        rewritten = await rewrite_question(state["question"], state["history"])
        state["standalone"] = rewritten
    except Exception:
        logger.warning("Rewrite failed, falling back to original", exc_info=True)
        state["standalone"] = state["question"]
    return state


# ----------------------------------------------------------------------
# Node: retrieve
# ----------------------------------------------------------------------
async def retrieve(state: Dict[str, Any]) -> Dict[str, Any]:
    _write_event({"status": "searching documents..."})
    query_emb = (await embed_texts([state["standalone"]], prefix="search_query: "))[0]
    hits = vector_search(query_emb, settings.top_k)
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
# Node: grade (optional relevance)
# ----------------------------------------------------------------------
async def grade(state: Dict[str, Any]) -> Dict[str, Any]:
    _write_event({"status": "Checking relevance..."})
    relevant = await guards.grade_relevance(
        state["question"],
        state.get("hits") or [],
        request_id=state.get("request_id"),
    )
    state["relevant"] = relevant
    if not relevant:
        state["retries"] = state.get("retries", 0) + 1
        logger.info(
            "grade_not_relevant",
            extra={
                "request_id": state.get("request_id"),
                "reason": "grade_no",
                "retries": state["retries"],
            },
        )
    return state


# ----------------------------------------------------------------------
# Node: generate (normal RAG answer)
# ----------------------------------------------------------------------
async def generate(state: Dict[str, Any]) -> Dict[str, Any]:
    messages = build_messages(state["question"], state.get("hits", []), state.get("history", []))
    parts: list[str] = []
    async for token in stream_chat(messages):
        parts.append(token)
        _write_event({"token": token})
    state["answer"] = "".join(parts)
    _write_event({"sources": state.get("sources", [])})
    return state


# ----------------------------------------------------------------------
# Node: output_check (post-stream verification only)
# ----------------------------------------------------------------------
async def output_check(state: Dict[str, Any]) -> Dict[str, Any]:
    answer = state.get("answer") or ""
    verification = guards.verify_output(
        answer,
        state.get("sources") or [],
        state.get("context") or "",
    )
    _write_event({"verification": verification})
    logger.info(
        "output_verification",
        extra={
            "request_id": state.get("request_id"),
            **verification,
        },
    )
    return state


# ----------------------------------------------------------------------
# Node: refuse (no hits / exhausted retries / not relevant)
# ----------------------------------------------------------------------
async def refuse(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(
        "refuse",
        extra={"request_id": state.get("request_id"), "reason": state.get("block_reason") or "not_found"},
    )
    for ch in NOT_FOUND_MESSAGE:
        _write_event({"token": ch})
    state["answer"] = NOT_FOUND_MESSAGE
    _write_event({"sources": []})
    return state