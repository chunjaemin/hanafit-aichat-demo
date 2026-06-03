import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rag_search_returns_chunks_key():
    """RAG 검색 응답에 chunks 키가 존재해야 한다."""
    response = client.post(
        "/api/v1/rag/search",
        json={"query": "청년 전세 대출", "top_k": 5},
    )
    assert response.status_code == 200
    assert "chunks" in response.json()
