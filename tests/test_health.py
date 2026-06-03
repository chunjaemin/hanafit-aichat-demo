import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_status_field():
    """Supabase 연결 여부와 관계없이 status 필드가 반환되어야 한다."""
    with patch("app.main.httpx.AsyncClient") as mock_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_resp
        mock_cls.return_value.__aenter__.return_value = mock_instance

        response = client.get("/health")
        assert response.status_code in (200, 503)
        body = response.json()
        assert "status" in body
        assert "supabase" in body


def test_health_degraded_when_supabase_down():
    """Supabase 연결 실패 시 503 + degraded를 반환해야 한다."""
    with patch("app.main.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("Connection refused")
        mock_cls.return_value.__aenter__.return_value = mock_instance

        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["status"] == "degraded"
