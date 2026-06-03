from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from app.core.config import settings

chat_llm   = ChatOpenAI(model=settings.CHAT_MODEL,   api_key=settings.OPENAI_API_KEY)
intent_llm = ChatOpenAI(model=settings.INTENT_MODEL, api_key=settings.OPENAI_API_KEY)

_async_openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_text(text: str) -> list[float]:
    res = await _async_openai.embeddings.create(
        model=settings.EMBED_MODEL,
        input=text,
    )
    return res.data[0].embedding
