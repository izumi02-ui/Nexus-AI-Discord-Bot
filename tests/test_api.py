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
    from utils.time_utils import iso, now_utc, now_utc

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


def test_chat_route_answers_smalltalk_without_a_provider(client):
    """Greeting handling must not depend on a model being reachable."""
    response = asyncio.run(
        client.post("/chat/", json={"user_id": 991_001, "message": "thanks!"})
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["response"].strip()
    assert body["route"]["type"] == "local"


def test_chat_route_returns_grounding_metadata(client, monkeypatch):
    from ai import provider_manager as pm

    text = "The rate is 5.50 percent, held steady today."

    async def fake_ask(self=None, **kwargs):
        return text

    async def fake_ask_with_info(self=None, **kwargs):
        return {
            "response": text,
            "provider": "Stub",
            "provider_key": "stub",
            "model": "stub-1",
            "seconds": 0.01,
        }

    monkeypatch.setattr(pm.provider_manager, "ask_with_info", fake_ask_with_info)
    monkeypatch.setattr(pm.provider_manager, "ask", fake_ask)

    from search.aggregator import aggregator
    from search.search_result import SearchResult
    from utils.time_utils import iso, now_utc

    evidence = SearchResult(
        title="Central bank holds",
        content="The central bank held its rate at 5.50 percent today.",
        source="Stub News",
        url="https://example.com/rate",
        confidence=0.9,
        published_at=iso(now_utc()),
    )

    confirmation = SearchResult(
        title="Central bank confirms",
        content="The central bank kept its rate at 5.50 percent today.",
        source="Second Stub News",
        url="https://second.example/rate",
        confidence=0.9,
        published_at=iso(now_utc()),
    )

    from search.report import SearchReport
    from search.ranking import ranking

    stub_report = SearchReport(
        query="what is the interest rate",
        results=[evidence, confirmation],
        cross=ranking.cross_check([evidence, confirmation]),
        tools_used=["brave"],
        freshness="short",
    )

    async def fake_search(*args, **kwargs):
        return stub_report

    monkeypatch.setattr(aggregator, "search", fake_search)

    response = asyncio.run(
        client.post(
            "/chat/",
            json={
                "user_id": 991_002,
                "message": "what is the interest rate today",
            },
        )
    )

    assert response.status_code == 200

    body = response.json()

    assert body["route"]["type"] == "search"
    assert body["grounded"] is True
    assert body["sources"][0]["url"] == "https://example.com/rate"
    assert "5.50 percent" in body["response"]


def test_research_route_reports_its_verdict(client, monkeypatch):
    from search.aggregator import aggregator
    from search.report import SearchReport
    from search.ranking import ranking
    from search.search_result import SearchResult
    from datetime import timedelta
    from utils.time_utils import now_utc

    rows = [
        SearchResult(
            title="Findings",
            content="The study found a 12% improvement over the previous method.",
            source="Journal",
            url="https://example.com/study",
            confidence=0.9,
            published_at=(now_utc() - timedelta(hours=3)).isoformat(),
        )
    ]

    report = SearchReport(
        query="quantum computing",
        results=rows,
        cross=ranking.cross_check(rows),
        tools_used=["arxiv"],
        freshness="medium",
    )

    async def fake_search(*args, **kwargs):
        return report

    monkeypatch.setattr(aggregator, "search", fake_search)

    response = asyncio.run(
        client.post("/research/", json={"topic": "quantum computing", "depth": 1})
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["sources"]
    assert body["verdict"]["confidence"] > 0
