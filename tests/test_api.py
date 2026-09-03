"""
API contract tests.

No LLM and no network in here: /chat is exercised only through routes that can
answer without a provider, and the evidence-shaped routes are checked for the
metadata callers need to show a grounding badge.
"""

import asyncio

import pytest

from api.app import app

httpx = pytest.importorskip("httpx")

from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest.fixture
def client():
    transport = ASGITransport(app=app)

    return AsyncClient(transport=transport, base_url="http://test")


def get(client, path):
    return asyncio.run(client.get(path))


def post(client, path, payload):
    return asyncio.run(client.post(path, json=payload))


def test_health_reports_the_real_state(client):
    response = asyncio.run(client.get("/health/"))

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "online"
    assert "provider" in body
    assert "tools" in body
    assert "self_update" in body
    assert "engine" in body


def test_tools_are_listed(client):
    response = asyncio.run(client.get("/tools/"))

    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_memory_route_reads_facts_and_window(client):
    from database.fact_manager import remember_fact

    remember_fact(777_001, "Home city: Pune", category="location", source="command")

    response = asyncio.run(client.get("/memory/777001"))

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert any("Pune" in fact["fact"] for fact in body["facts"])
    assert "stats" in body


def test_models_route_lists_available_providers(client):
    response = asyncio.run(client.get("/models/"))

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_search_route_returns_grounded_metadata(client, monkeypatch):
    """Stub the aggregator so the route's shape is tested, not the network."""
    from search.report import SearchReport
    from search.search_result import SearchResult
    from utils.time_utils import iso, now_utc

    stub = SearchReport(
        query="test query",
        results=[
            SearchResult(
                title="Stub",
                content="Stubbed evidence about the thing.",
                source="Stub News",
                url="https://example.com/stub",
                confidence=0.9,
                published_at=iso(now_utc()),
            )
        ],
        cross={"sources": 1, "corroborated": False, "confidence": 0.8, "top_confidence": 0.9},
        tools_used=["brave"],
        freshness="short",
    )

    from search.aggregator import aggregator

    async def fake_search(*args, **kwargs):
        return stub

    monkeypatch.setattr(aggregator, "search", fake_search)

    response = asyncio.run(
        client.post("/search/", json={"query": "test query"})
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["grounded"] is True
    assert body["results"][0]["url"] == "https://example.com/stub"
    assert body["summary"]["sources"] == 1
