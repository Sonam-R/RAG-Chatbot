from typing import AsyncIterator
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

SYSTEM_PROMPT = "You are a helpful assistant."

async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    stream = await client.chat.completions.create(
        model=settings.chat_model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta