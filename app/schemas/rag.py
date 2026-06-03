from pydantic import BaseModel


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    threshold: float = 0.1
    chunk_type: str | None = None  # summary | eligibility | content | application


class RagChunk(BaseModel):
    chunk_id: str
    chunk_type: str
    chunk_text: str
    similarity: float
    benefit_id: str
    service_name: str
    support_type: str | None = None
    ai_summary: str | None = None
    service_field: str | None = None
    target_users: str | None = None
    support_content: str | None = None
    application_method: str | None = None
    application_period_text: str | None = None
    application_url: str | None = None
    detail_url: str | None = None
    org_name: str | None = None
    org_phone: str | None = None


class RagSearchResponse(BaseModel):
    chunks: list[RagChunk]
