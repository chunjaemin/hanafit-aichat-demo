from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.clients.openai import chat_llm
from app.core.prompts.suggestion import SUGGESTION_SYSTEM_PROMPT


class SuggestedQuestionsResult(BaseModel):
    questions: list[str]


async def generate_suggestions(message: str, response_text: str) -> list[str]:
    structured_llm = chat_llm.with_structured_output(SuggestedQuestionsResult)

    content = f"사용자: {message}\n챗봇: {response_text}"
    messages = [
        SystemMessage(content=SUGGESTION_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]

    result = await structured_llm.ainvoke(messages)
    return result.questions[:3]
