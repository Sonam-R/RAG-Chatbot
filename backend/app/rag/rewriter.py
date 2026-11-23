import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Rewrite the last question as a standalone question, "
    "using the conversation for context. Output only the question."
)


def rewrite_question(question: str, history: list[dict]) -> str:
    """Turn a follow-up question into a standalone query for vector search."""
    if not history:
        return question

    n = settings.rewrite_history_turns * 2
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        *history[-n:],
        {"role": "user", "content": question},
    ]
    try:
        client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
        resp = client.chat.completions.create(
            model=settings.chat_model,
            messages=messages,
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip().strip("\"'")
    except Exception:
        logger.warning("Query rewrite failed; using the original question")
        return question
    return text or question
