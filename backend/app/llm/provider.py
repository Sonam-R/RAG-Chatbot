import asyncio
from typing import AsyncIterator

from ..core.config import settings

# Detect a mock API key (any key starting with "sk-mock")
# If detected, we will not call OpenAI but yield deterministic mock tokens.

if settings.openai_api_key.startswith("sk-mock"):
    async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
        # Simple deterministic mock response based on the last user message
        user_msg = messages[-1]["content"] if messages else ""
        response = f"Mock response to: {user_msg}"
        # Yield the response word‑by‑word to simulate streaming
        for word in response.split():
            await asyncio.sleep(0.01)
            yield word + " "
else:
    from openai import AsyncOpenAI
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


