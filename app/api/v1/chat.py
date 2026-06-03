import logging
from fastapi import APIRouter
from app.schemas.chat import ChatProcessRequest, ChatProcessResponse
from app.services import intent as intent_service
from app.services import chat as chat_service
from app.services import suggestion as suggestion_service
from app.exceptions import ChatbotException

router = APIRouter()
logger = logging.getLogger("app")


@router.post("/process", response_model=ChatProcessResponse)
async def process_chat(request: ChatProcessRequest) -> ChatProcessResponse:
    intent_result = await intent_service.classify_intent(
        request.message, request.chat_history
    )

    intent = intent_result.intent

    if intent == "text_rag":
        # RAG 미구현 — text_simple로 폴백
        logger.warning("text_rag → text_simple 폴백 (RAG 미구현)")
        intent = "text_simple"

    if intent == "text_simple":
        text = await chat_service.generate_simple_response(
            request.message, request.chat_history, request.user_profile
        )
        suggestions = await suggestion_service.generate_suggestions(request.message, text)
        return ChatProcessResponse(
            intent=intent_result.intent,
            text=text,
            suggested_questions=suggestions,
            extracted_user_info=intent_result.extracted_user_info,
        )

    if intent == "benefit_cards":
        text = "맞춤 혜택 카드 기능은 준비 중이에요. 원하시는 혜택을 구체적으로 물어봐 주세요!"
        suggestions = await suggestion_service.generate_suggestions(request.message, text)
        return ChatProcessResponse(
            intent="benefit_cards",
            text=text,
            benefit_cards=[],
            suggested_questions=suggestions,
            extracted_user_info=intent_result.extracted_user_info,
        )

    raise ChatbotException(f"알 수 없는 intent: {intent}")
