import logging
from typing import AsyncIterator
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

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
        logging.getLogger(__name__).warning("Chat model warm-up failed", exc_info=True)
    try:
        await client.embeddings.create(
            model=settings.embed_model,
            input=["warm"],
            extra_body=_ollama_extra(),
        )
    except Exception:
        logging.getLogger(__name__).warning("Embedding model warm-up failed", exc_info=True)


async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    stream = await client.chat.completions.create(
        model=settings.chat_model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        stream=True,
        extra_body=_ollama_extra(),
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta