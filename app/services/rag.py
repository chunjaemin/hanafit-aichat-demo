from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.clients.openai import embed_text, chat_llm
from app.core.prompts.rag import RAG_SYSTEM_PROMPT
from app.repositories.vector import vector_repository
from app.schemas.chat import ChatMessage, UserProfile


def _format_context(docs: list[dict]) -> str:
    """검색된 청크들을 LLM 컨텍스트 문자열로 변환. 같은 혜택은 한 번만 표시."""
    if not docs:
        return "관련 혜택 정보를 찾지 못했습니다."

    seen: set[str] = set()
    blocks: list[str] = []

    for doc in docs:
        benefit_id = str(doc.get("benefit_id", ""))
        if benefit_id in seen:
            continue
        seen.add(benefit_id)

        lines = [f"【{doc.get('service_name', '(이름없음)')}】"]

        chunk_type = doc.get("chunk_type")

        if chunk_type == "summary":
            if doc.get("service_field"):
                lines.append(f"분야: {doc['service_field']}")
            if doc.get("ai_summary"):
                lines.append(f"요약: {doc['ai_summary']}")
            if doc.get("support_type"):
                lines.append(f"지원유형: {doc['support_type']}")

        elif chunk_type == "eligibility":
            if doc.get("target_users"):
                lines.append(f"지원대상: {doc['target_users']}")
            if doc.get("selection_criteria"):
                lines.append(f"선정기준: {doc['selection_criteria']}")

        elif chunk_type == "content":
            if doc.get("support_content"):
                lines.append(f"지원내용: {doc['support_content']}")
            if doc.get("support_type"):
                lines.append(f"지원유형: {doc['support_type']}")

        elif chunk_type == "application":
            if doc.get("application_method"):
                lines.append(f"신청방법: {doc['application_method']}")
            if doc.get("application_period_text"):
                lines.append(f"신청기간: {doc['application_period_text']}")
            if doc.get("required_documents"):
                lines.append(f"구비서류: {doc['required_documents']}")
            if doc.get("application_url"):
                lines.append(f"신청URL: {doc['application_url']}")

        if doc.get("org_name"):
            lines.append(f"제공처: {doc['org_name']}")
        if doc.get("detail_url"):
            lines.append(f"상세정보: {doc['detail_url']}")

        blocks.append("\n".join(lines))

    return "\n\n---\n\n".join(blocks)


async def generate_rag_response(
    message: str,
    chat_history: list[ChatMessage],
    user_profile: UserProfile | None = None,
) -> str:
    # 1. 쿼리 임베딩
    embedding = await embed_text(message)

    # 2. benefit_chunks 유사도 검색
    docs = await vector_repository.similarity_search(
        embedding=embedding,
        top_k=5,
        threshold=0.4,
    )

    # 3. 컨텍스트 구성
    context = _format_context(docs)

    # 4. 시스템 프롬프트 + 컨텍스트 조합
    system_content = f"{RAG_SYSTEM_PROMPT}\n\n[관련 혜택 정보]\n{context}"
    if user_profile:
        profile_info = user_profile.model_dump(exclude_none=True)
        if profile_info:
            system_content += f"\n\n[사용자 프로필] {profile_info}"

    # 5. LLM 호출 (최근 6개 이전 대화 포함)
    messages = [
        SystemMessage(content=system_content),
        *[
            HumanMessage(content=m.content) if m.role == "user"
            else AIMessage(content=m.content)
            for m in chat_history[-6:]
        ],
        HumanMessage(content=message),
    ]

    result = await chat_llm.ainvoke(messages)
    return result.content
