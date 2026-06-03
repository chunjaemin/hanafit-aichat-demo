import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_process_requires_message():
    """message 필드 없이 요청 시 422를 반환해야 한다."""
    response = client.post("/api/v1/chat/process", json={})
    assert response.status_code == 422


def test_chat_process_response_schema():
    """정상 요청 시 응답에 intent, text, suggested_questions가 있어야 한다."""
    # 실제 OpenAI 호출이 필요하므로 .env 설정 후 통합 테스트로 실행
    pytest.skip("OpenAI API 키 필요 — 통합 테스트")
