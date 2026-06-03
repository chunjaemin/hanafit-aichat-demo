import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rag_search_returns_empty_list():
    """RAG 미구현 상태에서 빈 documents 배열을 반환해야 한다."""
    response = client.post(
        "/api/v1/rag/search",
        json={"query": "청년 전세 대출", "top_k": 5},
    )
    assert response.status_code == 200
    assert response.json()["documents"] == []
