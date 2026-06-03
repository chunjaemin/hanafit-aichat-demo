from langchain_openai import ChatOpenAI
from app.core.config import settings

chat_llm = ChatOpenAI(model=settings.CHAT_MODEL, api_key=settings.OPENAI_API_KEY)
intent_llm = ChatOpenAI(model=settings.INTENT_MODEL, api_key=settings.OPENAI_API_KEY)
