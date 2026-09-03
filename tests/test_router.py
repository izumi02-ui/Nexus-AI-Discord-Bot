"""
Request routing: does this message need tools, a calculation, or nothing?

These assertions are the cheapest defence against the two failure modes of a
"smart" bot: searching for everything (slow, rate-limited, and it makes the
model second-guess facts it already knows) and searching for nothing (halluc-
inated prices).
"""

import pytest

from ai.request_router import request_router


def route(text, **kwargs):
    return request_router.route(text, **kwargs)


def test_greeting_is_answered_by_the_model():
    decision = route("hi")

    assert decision["type"] == "chat"
    assert decision["tools"] == []
    assert decision["verification"] is False


def test_acknowledgements_do_not_trigger_a_search():
    for text in ("ok", "thanks!", "cool, thanks", "k"):
        assert route(text)["type"] == "local", text


def test_arithmetic_is_computed_not_generated():
    decision = route("what is 17*23")

    assert decision["calculator"] is True
    assert decision["tools"] == ["calculator"]
    assert decision["grounded"] is True


def test_percent_expression_is_computed():
    decision = route("what is 12% of 480")

    assert decision["calculator"] is True


def test_weather_uses_the_weather_tool_only():
    decision = route("weather in delhi right now")

    assert decision["type"] == "search"
    assert decision["freshness"] == "instant"
    assert "weather" in decision["tools"]
    # Padding with a web search would let a stale page dilute a live reading.
    assert decision["tools"] == ["weather"]


def test_clock_question_is_instant_and_exact():
    decision = route("what time is it in tokyo")

    assert decision["tools"] == ["time"]
    assert decision["budget"] <= 60


def test_currency_conversion_is_instant():
    decision = route("convert 100 usd to inr")

    assert decision["tools"] == ["currency"]


def test_current_role_holder_is_searched():
    decision = route("who is the prime minister of india")

    assert decision["type"] == "search"
    assert decision["freshness"] in {"instant", "short"}
    assert set(decision["tools"]) & {"wikipedia", "news", "brave", "google", "duckduckgo"}


def test_static_question_is_not_searched():
    for text in (
        "explain photosynthesis",
        "write a python function that reverses a linked list",
        "do you like my new savings account?",
    ):
        decision = route(text)

        assert decision["type"] == "chat", text
        assert decision["tools"] == [], text


def test_explicit_search_request_is_forced():
    decision = route("search for the latest stable python release")

    assert decision["force"] is True
    assert decision["type"] == "search"


def test_pasted_url_is_scraped():
    decision = route("what does this say https://example.com/post ?")

    assert "web_scraper" in decision["tools"]
    assert decision["urls"]


def test_translation_is_routed_to_the_translator():
    assert route("translate good morning to japanese")["tools"] == ["translator"]


def test_distance_is_routed_to_maps():
    assert route("how far is it from delhi to mumbai")["tools"] == ["maps"]


@pytest.mark.parametrize("mode", ["always", "never"])
def test_search_mode_override_is_respected(monkeypatch, mode):
    from utils.settings import settings

    monkeypatch.setattr(settings, "search_mode", mode)

    decision = route("explain photosynthesis")

    if mode == "always":
        assert decision["type"] == "search"
    else:
        assert decision["type"] in {"chat", "local"}


def test_empty_message_is_handled():
    assert route("")["type"] == "local"
    assert route("   ")["type"] == "local"


def test_instant_answers_are_not_cached():
    assert route("weather in delhi right now")["cacheable"] is False
    assert route("who is the prime minister of india")["cacheable"] is True
