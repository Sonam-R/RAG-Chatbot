import uuid
from contextlib import asynccontextmanager
from contextvars import Token

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.core.request_context import request_id_ctx
from app.db import models  # noqa: F401
from app.db.session import Base, engine
from app.llm.provider import warm_models

Base.metadata.create_all(bind=engine)

RATE_LIMIT_MESSAGE = "Too many requests. Please wait a moment and try again."


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry = getattr(exc, "retry_after", None) or 60
    return JSONResponse(
        status_code=429,
        content={"error": RATE_LIMIT_MESSAGE},
        headers={"Retry-After": str(int(retry))},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await warm_models()
    yield


app = FastAPI(
    title="RAG Chatbot",
    description="FastAPI backend that streams OpenAI responses.",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    token: Token = request_id_ctx.set(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        request_id_ctx.reset(token)


app.include_router(chat_router)
app.include_router(documents_router)


@app.get("/health")
@limiter.limit(settings.rate_limit_default)
async def health(request: Request):
    return {"status": "ok"}