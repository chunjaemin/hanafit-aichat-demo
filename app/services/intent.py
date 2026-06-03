from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.clients.openai import intent_llm
from app.schemas.chat import ChatMessage, ExtractedUserInfo
from app.core.prompts.intent import INTENT_SYSTEM_PROMPT


class IntentResult(BaseModel):
    intent: Literal["text_rag", "text_simple", "benefit_cards"]
    extracted_user_info: ExtractedUserInfo


async def classify_intent(message: str, chat_history: list[ChatMessage]) -> IntentResult:
    structured_llm = intent_llm.with_structured_output(IntentResult)

    messages = [
        SystemMessage(content=INTENT_SYSTEM_PROMPT),
        *[
            HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
            for m in chat_history[-4:]
        ],
        HumanMessage(content=message),
    ]

    return await structured_llm.ainvoke(messages)
