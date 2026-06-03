from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.clients.openai import embed_text, chat_llm
from app.clients.supabase import supabase_client
from app.schemas.chat import ChatMessage, UserProfile
from app.core.prompts.chat import CHAT_SYSTEM_PROMPT


async def search_benefits(
    query: str,
    top_k: int = 5,
    threshold: float = 0.1,
    chunk_type: str | None = None,
) -> list[dict]:
    embedding = await embed_text(query)
    result = supabase_client.rpc(
        "match_benefits",
        {
            "query_embedding": embedding,
            "filter_chunk_type": chunk_type,
            "match_threshold": threshold,
            "match_count": top_k,
        },
    ).execute()
    return result.data or []


def _format_chunk(c: dict) -> str:
    lines = [f"[{c['service_name']}]"]
    if c.get("ai_summary"):
        lines.append(f"요약: {c['ai_summary']}")
    if c.get("target_users"):
        lines.append(f"대상: {c['target_users']}")
    if c.get("support_content"):
        lines.append(f"지원내용: {c['support_content']}")
    if c.get("application_method"):
        lines.append(f"신청방법: {c['application_method']}")
    if c.get("application_period_text"):
        lines.append(f"신청기간: {c['application_period_text']}")
    if c.get("application_url"):
        lines.append(f"신청URL: {c['application_url']}")
    if c.get("detail_url"):
        lines.append(f"상세URL: {c['detail_url']}")
    if c.get("org_name"):
        lines.append(f"제공처: {c['org_name']}")
    return "\n".join(lines)


async def generate_rag_response(
    message: str,
    chat_history: list[ChatMessage],
    user_profile: UserProfile | None = None,
) -> str:
    system_content = CHAT_SYSTEM_PROMPT
    if user_profile:
        profile_info = user_profile.model_dump(exclude_none=True)
        if profile_info:
            system_content += f"\n\n사용자 프로필: {profile_info}"

    chunks = await search_benefits(message, top_k=5)
    if chunks:
        context = "\n\n---\n\n".join(_format_chunk(c) for c in chunks)
        system_content += f"\n\n## 관련 혜택 정보\n아래 정보를 바탕으로 답변하세요. URL이 있으면 반드시 포함하세요.\n{context}"

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
