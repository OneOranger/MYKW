from fastapi.testclient import TestClient

from aipayment_kb_agent.api.dependencies import get_agent
from aipayment_kb_agent.config.settings import get_settings


def test_query_api_smoke():
    get_settings.cache_clear()
    get_agent.cache_clear()
    from aipayment_kb_agent.api.app import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/query",
        json={"session_id": "s1", "message": "什么是RAG？", "auto_upgrade": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert "meta" in data
