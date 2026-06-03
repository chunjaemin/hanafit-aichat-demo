from fastapi import APIRouter
from app.schemas.rag import RagSearchRequest, RagSearchResponse, RagChunk
from app.services.rag import search_benefits

router = APIRouter()


@router.post("/search", response_model=RagSearchResponse)
async def rag_search(request: RagSearchRequest) -> RagSearchResponse:
    docs = await search_benefits(request.query, top_k=request.top_k, threshold=request.threshold, chunk_type=request.chunk_type)
    return RagSearchResponse(chunks=[RagChunk(**d) for d in docs])
