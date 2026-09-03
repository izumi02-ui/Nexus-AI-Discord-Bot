"""
Prompt assembly: the model must see evidence, memory and its limits, and the
budget must be enforced by dropping the least important block first.
"""

import asyncio
from datetime import timedelta

from ai.conversation_manager import CHAR_BUDGET, conversation_manager
from search.report import SearchReport
from utils.prompt_loader import build_system_prompt
from utils.time_utils import now_utc


def make_report(result, *extra):
    from search.ranking import ranking

    rows = [result, *extra]

    return SearchReport(
        query="population of tokyo",
        results=rows,
        cross=ranking.cross_check(rows),
    )


def build(**kwargs):
    return asyncio.run(conversation_manager.build(**kwargs))


def test_system_prompt_states_the_accuracy_policy():
    prompt = build_system_prompt()

    assert "Grounding and accuracy" in prompt
    assert "never invent" in prompt.lower() or "do not invent" in prompt.lower()
    assert "training cutoff" in prompt.lower()


def test_system_prompt_carries_the_real_clock():
    prompt = build_system_prompt()

    today = now_utc().strftime("%d %B %Y")

    assert today in prompt, "the runtime date must be injected, not remembered"
    assert "IST" in prompt


def test_system_prompt_reports_the_running_version():
    from config import VERSION

    assert VERSION in build_system_prompt()


def test_evidence_block_is_included_when_a_report_exists(result):
    evidence = result(
        title="Census",
        content="Tokyo's population is 14.1 million.",
        url="https://example.com/tokyo",
        source="Census Office",
    )

    conversation = build(
        user_id=987_654,
        message="what is the population of tokyo",
        report=make_report(evidence),
    )

    joined = "\n".join(
        message.get("content", "")
        if isinstance(message, dict)
        else getattr(message, "content", "")
        for message in conversation
    )

    assert "14.1 million" in joined
    assert conversation[-1]["role"] in ("user", " Human")


def test_memory_block_is_separate_from_evidence(result, monkeypatch):
    from database import fact_manager

    fact_manager.remember_fact(
        555_001,
        "Allergies: peanuts",
        category="health",
        source="command",
    )

    evidence = result(
        content="Peanut allergy is common.",
        url="https://example.com/a",
    )

    conversation = build(
        user_id=555_001,
        message="is a peanut safe for me",
        report=make_report(evidence),
    )

    system = " ".join(
        message.get("content", "") for message in conversation if message["role"] == "system"
    )

    assert "peanuts" in system.lower()
    assert "MEMORY" in system.upper() or "FACTS" in system.upper()


def test_overlong_evidence_is_dropped_before_the_persona(result):
    huge = result(
        content=("a very long passage " * 400)[:12000],
        url="https://example.com/huge",
    )

    conversation = build(
        user_id=987_655,
        message="summarise this",
        report=make_report(*[huge] * 6),
    )

    total = sum(len(message.get("content", "")) for message in conversation)

    assert total <= CHAR_BUDGET + 500

    system = conversation[0]["content"]

    assert "Project Nexus" in system  # persona survives truncation


def test_verified_notes_are_hidden_when_live_evidence_exists(result, monkeypatch):
    from database import knowledge

    knowledge.clear_all()

    knowledge.remember(
        "Tokyo's population is 12.0 million.",
        topic="population tokyo",
        source="Old Note",
        url="https://example.com/old",
        confidence=0.9,
        ttl_seconds=3600,
    )

    fresh = result(
        content="Tokyo's population is 14.1 million.",
        url="https://example.com/new",
        published=(now_utc() - timedelta(minutes=5)).isoformat(),
    )

    conversation = build(
        user_id=987_656,
        message="what is the population of tokyo",
        report=make_report(fresh),
        remembered=knowledge.recall("population of tokyo", min_confidence=0.4),
    )

    system = " ".join(
        message["content"] for message in conversation if message["role"] == "system"
    )

    assert "14.1 million" in system
    assert "12.0 million" not in system


def test_retry_instruction_is_appended_when_asked(result):
    conversation = build(
        user_id=987_657,
        message="population of osaka",
        retry_instruction="Answer again using only the evidence block.",
    )

    joined = " ".join(message["content"] for message in conversation)

    assert "Answer again using only the evidence block." in joined
