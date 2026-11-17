import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..llm.provider import stream_chat

router = APIRouter(prefix="/api")

class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]

@router.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        try:
            async for token in stream_chat([m.model_dump() for m in req.messages]):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': 'Something went wrong'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
