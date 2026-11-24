import logging
import re
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Rewrite the last question as a standalone question, "
    "using the conversation for context. Output only the question."
)

_REFERENCE_WORDS = frozenset(
    {
        "it",
        "its",
        "that",
        "this",
        "those",
        "these",
        "they",
        "them",
        "he",
        "she",
        "one",
        "ones",
        "former",
        "latter",
        "same",
        "also",
    }
)
_REFERENCE_PHRASES = ("what about", "how about")
_WORD_RE = re.compile(r"\b\w+\b")


def needs_rewrite(question: str, history: list[dict]) -> bool:
    """Return True when a follow-up should be expanded before retrieval."""
    if not history:
        return False
    text = question.strip()
    if len(text.split()) < 6:
        return True
    lower = text.lower()
    for phrase in _REFERENCE_PHRASES:
        if phrase in lower:
            return True
    words = _WORD_RE.findall(lower)
    if any(w in _REFERENCE_WORDS for w in words):
        return True
    return False


def rewrite_question(question: str, history: list[dict]) -> str:
    """Turn a follow-up question into a standalone query for vector search."""
    if not history or not needs_rewrite(question, history):
        return question

    n = settings.rewrite_history_turns * 2
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        *history[-n:],
        {"role": "user", "content": question},
    ]
    model = settings.rewriter_model or settings.chat_model
    try:
        client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_seconds,
        )
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=64,
            extra_body={"keep_alive": settings.ollama_keep_alive},
        )
        text = (resp.choices[0].message.content or "").strip().strip("\"'")
    except Exception:
        logger.warning("Query rewrite failed; using the original question")
        return question
    return text or question