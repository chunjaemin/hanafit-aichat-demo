from app.clients.supabase import supabase_client


class VectorRepository:
    async def similarity_search(
        self, embedding: list[float], top_k: int = 5, threshold: float = 0.7
    ) -> list[dict]:
        # RAG 구현 시 활성화
        raise NotImplementedError("RAG 미구현 — supabase/init.sql 실행 후 활성화")

    async def insert_document(self, content: str, embedding: list[float], metadata: dict = {}) -> str:
        raise NotImplementedError("RAG 미구현")


vector_repository = VectorRepository()
