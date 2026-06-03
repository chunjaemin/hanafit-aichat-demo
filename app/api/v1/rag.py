from fastapi import APIRouter
from app.schemas.rag import RagSearchRequest, RagSearchResponse

router = APIRouter()


@router.post("/search", response_model=RagSearchResponse)
async def rag_search(request: RagSearchRequest) -> RagSearchResponse:
    # RAG 구현 예정 — supabase/init.sql 실행 후 활성화
    return RagSearchResponse(documents=[])
