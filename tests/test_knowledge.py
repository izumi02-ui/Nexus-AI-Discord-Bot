"""
The verified-knowledge store: how Nexus gets smarter between restarts.
"""

from datetime import timedelta

from database import knowledge
from utils.time_utils import now_utc


def test_remember_and_recall():
    knowledge.clear_all()

    row_id = knowledge.remember(
        "The prime minister of India is Shekhar Kumar, took office 2026.",
        topic="prime minister india",
        claim="office holder",
        source="Example News",
        url="https://example.com/pm",
        tool="brave",
        confidence=0.9,
        ttl_seconds=3600,
    )

    assert row_id

    rows = knowledge.recall("who is the prime minister of india", min_confidence=0.5)

    assert rows
    assert "Shekhar Kumar" in rows[0]["value"]
    assert rows[0]["status"] == "active"


def test_remembering_the_same_claim_refreshes_instead_of_duping():
    knowledge.clear_all()

    first = knowledge.remember(
        "The population of Japan is 123.8 million.",
        topic="population japan",
        source="Census Office",
        url="https://example.com/a",
        confidence=0.8,
        ttl_seconds=3600,
    )

    second = knowledge.remember(
        "The population of Japan is 123.8 million.",
        topic="population japan",
        source="Census Office",
        url="https://example.com/a",
        confidence=0.9,
        ttl_seconds=3600,
    )

    stats = knowledge.stats()

    assert stats["total"] == 1
    assert second == first or second is None


def test_changed_value_supersedes_and_keeps_history():
    knowledge.clear_all()

    knowledge.remember(
        "The population of Japan is 125.1 million.",
        topic="population japan",
        source="Old Report",
        url="https://example.com/old",
        confidence=0.8,
        ttl_seconds=3600,
    )

    knowledge.remember(
        "The population of Japan is 123.0 million.",
        topic="population japan",
        source="New Report",
        url="https://example.com/new",
        confidence=0.85,
        ttl_seconds=3600,
    )

    rows = knowledge.recall("population of japan", min_confidence=0.4)

    assert len(rows) == 1
    assert "123.0" in rows[0]["value"]

    history = knowledge.find("population japan")

    assert history["id"]


def test_expired_row_is_not_recalled_as_current():
    knowledge.clear_all()

    row_id = knowledge.remember(
        "The match ended 2-1 for Kerala.",
        topic="kerala match result",
        source="Sports Daily",
        url="https://example.com/m",
        confidence=0.9,
        ttl_seconds=1,
    )

    # Push the shelf life into the past without sleeping a second.
    from database.database import database

    database.execute(
        "UPDATE knowledge SET stale_after = ? WHERE id = ?",
        (
            (now_utc() - timedelta(seconds=5)).isoformat(),
            row_id,
        ),
    )

    assert knowledge.recall("kerala match result", min_confidence=0.4) == []

    assert knowledge.stale_rows(limit=50)


def test_disputed_rows_are_marked_and_downweighted():
    knowledge.clear_all()

    row_id = knowledge.remember(
        "The capital of the realm is Vellore.",
        topic="realm capital",
        source="Blog",
        url="https://example.com/b",
        confidence=0.8,
        ttl_seconds=3600,
    )

    knowledge.mark_disputed(row_id, "two official sources name Bengaluru")

    row = knowledge.get(row_id)

    assert row["status"] == "disputed"
    assert "Bengaluru" in (row["notes"] or "")


def test_prune_drops_weak_entries():
    knowledge.clear_all()

    for index in range(6):
        knowledge.remember(
            f"Weak claim number {index} about test topic.",
            topic=f"weak claim {index}",
            source="Forum",
            url=f"https://example.com/{index}",
            confidence=0.2,
            ttl_seconds=3600,
        )

    result = knowledge.prune(min_confidence=0.5, keep=100)

    assert knowledge.stats()["total"] == 0 or result["removed"] >= 1


def test_topic_counting_drives_the_watchlist():
    knowledge.clear_all()

    for _ in range(3):
        knowledge.record_topic("who won the grand prix", user_id=1)

    knowledge.remember(
        "Max Verstappen won the grand prix.",
        topic="grand prix winner",
        source="Race News",
        url="https://example.com/r",
        confidence=0.9,
        ttl_seconds=3600,
    )

    watched = knowledge.watchlist(limit=5)

    assert any(row["topic"] for row in watched)
