import json
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..llm.provider import stream_chat
from ..db.session import SessionLocal
from ..db.models import Conversation, Message

router = APIRouter(prefix="/api")

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@router.post("/chat")
async def chat(req: ChatRequest):
    db = SessionLocal()
    try:
        # Retrieve existing conversation or create a new one
        if req.conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
            if not conv:
                conv = Conversation(id=req.conversation_id)
                db.add(conv)
                db.commit()
                db.refresh(conv)
        else:
            conv = Conversation()
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # Store the user's message
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=req.message,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Gather full conversation history for the LLM
        history = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id)
            .all()
        )
        messages_for_llm = [{"role": m.role, "content": m.content} for m in history]

        async def event_stream():
            # First send the conversation ID so the client can keep track
            yield f"data: {json.dumps({'conversation_id': conv.id})}\n\n"
            try:
                async for token in stream_chat(messages_for_llm):
                    yield f"data: {json.dumps({'token': token})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception:
                yield f"data: {json.dumps({'error': 'Something went wrong'})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    finally:
        db.close()
