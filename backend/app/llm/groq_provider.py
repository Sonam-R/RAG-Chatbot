import logging
from typing import AsyncIterator

from openai import AsyncOpenAI, APIConnectionError, APITimeoutError

from app.core.config import settings
from app.core.errors import ModelUnavailableError, map_openai_error

logger = logging.getLogger(__name__)

# Groq client – uses its own base URL and API key (both configurable)
_groq_client = AsyncOpenAI(
    base_url=settings.groq_base_url,
    api_key=settings.groq_api_key,
    timeout=settings.llm_timeout_seconds,
)

SYSTEM_PROMPT = "You are a helpful assistant."

async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    """Stream a chat completion from Groq.

    Any network/connection/API error is normalised to ``ModelUnavailableError``
    so the caller can decide to fall back to another provider.
    """
    try:
        stream = await _groq_client.chat.completions.create(
            model=settings.groq_chat_model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            temperature=settings.chat_temperature,
            stream=True,
        )
    except Exception as exc:
        # Convert known OpenAI‑compatible errors to our unified ModelUnavailableError
        try:
            map_openai_error(exc)
        except ModelUnavailableError:
            raise
        if isinstance(exc, (APIConnectionError, APITimeoutError)):
            raise ModelUnavailableError() from exc
        raise ModelUnavailableError() from exc

    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
