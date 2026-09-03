"""
The self-update cycle: proof that Nexus re-checks and corrects itself.

Everything here is offline - the aggregator is stubbed, so what is under test is
the *policy* (confirm / correct / refuse to believe / prune), not the network.
"""

import asyncio

from database import knowledge
from database.database import database
from search.report import SearchReport
from utils.time_utils import iso, now_utc


def report_for(result, content, url="https://example.com/live"):
    from search.ranking import ranking

    rows = [
        result(
            title="Live source says",
            content=content,
            url=url,
            source="Live Paper",
            confidence=0.9,
            published=iso(now_utc()),
        )
    ]

    return SearchReport(
        query="q",
        results=rows,
        cross=ranking.cross_check(rows),
        tools_used=["brave"],
        freshness="short",
    )


def seed(topic, value, *, stale=True, confidence=0.8):
    knowledge.clear_all()

    row_id = knowledge.remember(
        value,
        topic=topic,
        claim="test claim",
        source="Old Source",
        url="https://example.com/old",
        tool="brave",
        confidence=confidence,
        ttl_seconds=3600,
    )

    if stale:
        from datetime import timedelta

        database.execute(
            "UPDATE knowledge SET stale_after = ? WHERE id = ?",
            ((now_utc() - timedelta(minutes=5)).isoformat(), row_id),
        )

    return row_id


def test_confirmed_claim_gains_confidence_and_is_not_rewritten(result, monkeypatch):
    from core.updater import updater

    row_id = seed("population of japan", "The population of Japan is 123.8 million.")

    async def fake_refresh(query, tools=None, **kwargs):
        return report_for(
            result,
            "The population of Japan is 123.8 million, the census office said.",
        )

    monkeypatch.setattr(updater, "_tools_for", lambda *a, **k: ["brave"], raising=False)
    monkeypatch.setattr("core.updater.aggregator.refresh", fake_refresh)

    summary = asyncio.run(updater.reverify_knowledge(limit=5))

    assert summary["checked"] == 1
    assert summary["confirmed"] == 1

    row = knowledge.get(row_id)

    assert row["status"] == "active"
    assert "123.8" in row["value"]


def test_changed_claim_is_corrected_and_the_cache_invalidated(result, monkeypatch):
    from core.updater import updater

    row_id = seed("population of japan", "The population of Japan is 125.1 million.")

    async def fake_refresh(query, tools=None, **kwargs):
        return report_for(
            result,
            "The population of Japan fell to 123.0 million in 2026.",
        )

    monkeypatch.setattr(updater, "_tools_for", lambda *a, **k: ["brave"], raising=False)
    monkeypatch.setattr("core.updater.aggregator.refresh", fake_refresh)

    summary = asyncio.run(updater.reverify_knowledge(limit=5))

    assert summary["updated"] == 1

    rows = knowledge.recall("population of japan", min_confidence=0.3)

    assert "123.0" in rows[0]["value"]
    assert "125.1" not in rows[0]["value"]

    topic = knowledge.get(row_id)["topic"]

    history = database.fetchall(
        "SELECT reason, old_value FROM knowledge_history WHERE topic = ?",
        (topic,),
    )

    assert history, "a self-correction must be recorded, not silently applied"
    assert any("125.1" in (row["old_value"] or "") for row in history)


def test_off_topic_evidence_is_refused_instead_of_filed(result, monkeypatch):
    """
    The dangerous failure mode of a self-updating bot: storing whatever a
    background search happened to return. A refresh that comes back about
    something else must not overwrite a real answer.
    """
    from core.updater import updater

    row_id = seed("prime minister india", "The prime minister of India is Shekhar Kumar.")

    async def fake_refresh(query, tools=None, **kwargs):
        return report_for(result, "Current time in Delhi: 07:47 PM — UTC+5:30.")

    monkeypatch.setattr(updater, "_tools_for", lambda *a, **k: ["brave"], raising=False)
    monkeypatch.setattr("core.updater.aggregator.refresh", fake_refresh)

    summary = asyncio.run(updater.reverify_knowledge(limit=5))

    assert summary.get("irrelevant") == 1

    row = knowledge.get(row_id)

    assert "Shekhar Kumar" in row["value"]
    assert "Current time" not in row["value"]
    assert row["status"] == "stale"


def test_unreachable_recheck_marks_stale_instead_of_trusting_nothing(result, monkeypatch):
    from core.updater import updater

    row_id = seed("kerala weather today", "Kerala is 31 C with light rain.")

    async def fake_refresh(query, tools=None, **kwargs):
        return SearchReport(query=query, results=[], error="all tools failed")

    monkeypatch.setattr(updater, "_tools_for", lambda *a, **k: ["brave"], raising=False)
    monkeypatch.setattr("core.updater.aggregator.refresh", fake_refresh)

    summary = asyncio.run(updater.reverify_knowledge(limit=5))

    assert summary["unreachable"] == 1
    assert knowledge.get(row_id)["status"] == "stale"


def test_maintenance_bounds_the_store():
    from core.updater import updater

    for index in range(4):
        knowledge.remember(
            f"Throwaway claim {index} about nothing in particular.",
            topic=f"throwaway {index}",
            source="Forum",
            url=f"https://example.com/{index}",
            confidence=0.1,
            ttl_seconds=3600,
        )

    result = updater.maintain()

    assert "cache_entries_removed" in result
    assert result["knowledge_pruned"]["low_confidence"] >= 1


def test_status_is_reportable_for_admin_commands():
    from core.updater import updater

    status = updater.status()

    for key in ("cycles", "last_cycle_at", "enabled", "interval_seconds", "knowledge", "cache"):
        assert key in status

    assert status["interval_seconds"] >= 60
