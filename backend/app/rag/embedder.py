import asyncio
import logging

from openai import APIConnectionError, APITimeoutError

from app.core.config import settings
from app.core.errors import ModelUnavailableError, map_openai_error
from app.llm.provider import client

logger = logging.getLogger(__name__)
BATCH = 32


async def embed_texts(texts: list[str], prefix: str = "") -> list[list[float]]:
    """Convert strings into embedding vectors using the shared LLM client."""
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        batch = [prefix + t for t in texts[i : i + BATCH]]
        try:
            resp = await asyncio.wait_for(
                client.embeddings.create(
                    model=settings.embed_model,
                    input=batch,
                    extra_body={"keep_alive": settings.ollama_keep_alive},
                ),
                timeout=settings.embed_timeout_seconds,
            )
        except Exception as exc:
            logger.exception("Embedding request failed")
            try:
                map_openai_error(exc)
            except ModelUnavailableError:
                raise
            if isinstance(exc, (APIConnectionError, APITimeoutError, TimeoutError, asyncio.TimeoutError)):
                raise ModelUnavailableError() from exc
            raise
        out.extend(d.embedding for d in resp.data)
    return out