import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

from app.core.config import settings
from app.api.v1 import chat, benefits, rag
from app.exceptions import ChatbotException
from app.middlewares.logging import LoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("app").info("하나청년 챗봇 AI 서버 시작")
    yield
    logging.getLogger("app").info("서버 종료")


app = FastAPI(
    title="하나청년 챗봇 AI 서버",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(benefits.router, prefix="/api/v1/benefits", tags=["benefits"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])


@app.exception_handler(ChatbotException)
async def chatbot_exception_handler(request: Request, exc: ChatbotException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.get("/health", tags=["health"])
async def health_check():
    supabase_ok = False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/",
                headers={"apikey": settings.SUPABASE_KEY},
                timeout=5.0,
            )
            supabase_ok = resp.status_code < 500
    except Exception:
        pass

    return JSONResponse(
        status_code=200 if supabase_ok else 503,
        content={
            "status": "ok" if supabase_ok else "degraded",
            "supabase": "connected" if supabase_ok else "disconnected",
        },
    )
