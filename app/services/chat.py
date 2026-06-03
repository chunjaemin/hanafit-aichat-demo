from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.clients.openai import chat_llm
from app.schemas.chat import ChatMessage, UserProfile
from app.core.prompts.chat import CHAT_SYSTEM_PROMPT


async def generate_simple_response(
    message: str,
    chat_history: list[ChatMessage],
    user_profile: UserProfile | None = None,
) -> str:
    system_content = CHAT_SYSTEM_PROMPT
    if user_profile:
        profile_info = user_profile.model_dump(exclude_none=True)
        if profile_info:
            system_content += f"\n\n사용자 프로필: {profile_info}"

    messages = [
        SystemMessage(content=system_content),
        *[
            HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
            for m in chat_history
        ],
        HumanMessage(content=message),
    ]

    result = await chat_llm.ainvoke(messages)
    return result.content
