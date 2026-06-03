from pydantic import BaseModel


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RagDocument(BaseModel):
    id: str
    content: str
    score: float


class RagSearchResponse(BaseModel):
    documents: list[RagDocument]
