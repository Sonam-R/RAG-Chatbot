import logging
from typing import AsyncIterator

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI

from app.core.config import settings
from app.core.errors import ModelUnavailableError, map_openai_error

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
    timeout=settings.llm_timeout_seconds,
)

SYSTEM_PROMPT = "You are a helpful assistant."


def _ollama_extra() -> dict[str, str]:
    return {"keep_alive": settings.ollama_keep_alive}


async def warm_models() -> None:
    """Load chat and embedding models into Ollama memory (best-effort)."""
    try:
        await client.chat.completions.create(
            model=settings.chat_model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
            extra_body=_ollama_extra(),
        )
    except Exception:
        logger.warning("Chat model warm-up failed", exc_info=True)
    try:
        await client.embeddings.create(
            model=settings.embed_model,
            input=["warm"],
            extra_body=_ollama_extra(),
        )
    except Exception:
        logger.warning("Embedding model warm-up failed", exc_info=True)


async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    try:
        stream = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            stream=True,
            extra_body=_ollama_extra(),
        )
    except Exception as exc:
        try:
            map_openai_error(exc)
        except ModelUnavailableError:
            raise
        if isinstance(exc, (APIConnectionError, APITimeoutError)):
            raise ModelUnavailableError() from exc
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
        if isinstance(exc, (APIConnectionError, APITimeoutError)):
            raise ModelUnavailableError() from exc
        raise