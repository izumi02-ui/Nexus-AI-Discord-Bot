"""
Freshness classification: the policy that decides when Nexus must look
something up, and when it must not waste a search.
"""

from search.freshness import (
    ETERNAL,
    INSTANT,
    LONG,
    MEDIUM,
    SHORT,
    budget_for,
    classify,
    is_answerable_from_memory,
    needs_fresh_evidence,
)

#: Answer changes by the minute - tools only, cache life measured in minutes.
INSTANT_QUESTIONS = [
    "what is the weather in delhi right now",
    "price of bitcoin today",
    "convert 100 usd to inr",
    "what time is it in tokyo",
    "is the stock market open now",
]

#: Answer changes daily or weekly - search, moderate cache.
SENSITIVE_QUESTIONS = [
    "who is the prime minister of india",
    "latest python version",
    "who won the match last night",
    "did they release the sequel yet",
    "best GPU for 1080p in 2025",
]

#: Slow-moving statistics: worth a lookup, not worth a panic.
SLOW_QUESTIONS = [
    "population of japan",
    "what is the capital of france",
]

#: Stable knowledge or pure reasoning: searching wastes time and adds noise.
STATIC_QUESTIONS = [
    "explain photosynthesis",
    "why is the sky blue",
    "write a python function to reverse a string",
    "what does 'sui generis' mean",
]


def test_instant_questions_are_instant():
    for query in INSTANT_QUESTIONS:
        assert classify(query) == "instant", query
        assert needs_fresh_evidence(query), query
        assert budget_for(query) == INSTANT, query


def test_current_events_are_searched():
    for query in SENSITIVE_QUESTIONS:
        assert classify(query) in {"instant", "short", "medium"}, query
        assert needs_fresh_evidence(query) or classify(query) == "medium", query


def test_slow_facts_get_a_wide_but_finite_budget():
    for query in SLOW_QUESTIONS:
        assert classify(query) in {"medium", "long"}, query
        assert budget_for(query) >= MEDIUM, query
        assert budget_for(query) < ETERNAL, query


def test_static_knowledge_is_answered_without_searching():
    for query in STATIC_QUESTIONS:
        assert classify(query) == "static", query
        assert not needs_fresh_evidence(query), query
        assert is_answerable_from_memory(query), query
        assert budget_for(query) == ETERNAL, query


def test_budgets_increase_with_stability():
    assert INSTANT < SHORT < MEDIUM < LONG < ETERNAL


def test_unknown_shapes_default_to_static():
    # An odd phrasing must not trigger a search storm on every message.
    assert classify("hmm interesting thought about gravity") == "static"


def test_a_year_in_the_question_means_recency():
    """"best X in 2025" is a question about the present wearing a year's clothes."""
    assert classify("what are the best budget phones in 2026") == "short"


def test_confidence_decays_with_age():
    from search.freshness import confidence_from_age

    fresh = confidence_from_age(60, INSTANT)
    stale = confidence_from_age(6 * 3600, INSTANT)

    assert fresh > stale
    assert stale >= 0.35  # floored, never zero - old news is not worthless news
    assert confidence_from_age(None, SHORT) < confidence_from_age(0, SHORT)
