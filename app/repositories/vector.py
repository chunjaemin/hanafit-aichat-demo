import asyncio
from app.clients.supabase import supabase_client


class VectorRepository:
    async def similarity_search(
        self,
        embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.4,
        chunk_type: str | None = None,
    ) -> list[dict]:
        def _rpc():
            return supabase_client.rpc(
                "match_benefits",
                {
                    "query_embedding": embedding,
                    "filter_chunk_type": chunk_type,
                    "match_threshold": threshold,
                    "match_count": top_k,
                },
            ).execute()

        result = await asyncio.to_thread(_rpc)
        return result.data or []


vector_repository = VectorRepository()
