from typing import AsyncIterator

from openai import AsyncOpenAI
from ..core.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = "You are a helpful assistant."

async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    stream = await client.chat.completions.create(
        model=settings.chat_model,
        messages=full_messages,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
