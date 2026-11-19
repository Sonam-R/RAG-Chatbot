# backend/app/llm/provider.py
import asyncio
from typing import AsyncIterator
import httpx2 as httpx
from ..core.config import settings

# ----------------------------------------------------------------------
# Mock fallback (kept for dev)
# ----------------------------------------------------------------------
if settings.openai_api_key.startswith("sk-mock"):
    async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
        user_msg = messages[-1]["content"] if messages else ""
        response = f"Mock response to: {user_msg}"
        for word in response.split():
            await asyncio.sleep(0.01)
            yield word + " "

# ----------------------------------------------------------------------
# Ollama path (enabled when USE_OLLAMA=true)
# ----------------------------------------------------------------------
elif settings.use_ollama:
    async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
        system_prompt = "You are a helpful assistant."
        payload = {
            "model": settings.chat_model,          # e.g. "llama3.2"
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "stream": True,
        }
        async with httpx.AsyncClient(base_url=settings.ollama_base_url) as client:
            async with client.stream("POST", "/chat/completions", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    data = httpx.Response(200, content=raw).json()
                    # OpenAI‑compatible shape: choices[0].delta.content
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]

# ----------------------------------------------------------------------
# Original OpenAI path (kept for completeness)
# ----------------------------------------------------------------------
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