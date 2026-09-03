"""
Tool-layer invariants: the rules every evidence source must obey.

These are the guarantees the pipeline relies on when it decides whether an
answer is grounded - a tool that lies about being available, or that returns
friendly filler, breaks accuracy further up the stack in a way no prompt can
fix.
"""

import asyncio

import pytest


def test_three_failures_take_a_tool_out_of_selection():
    from tools.base import ToolHealth

    health = ToolHealth()

    assert health.degraded is False

    for _ in range(2):
        health.record_failure("timeout")

    assert health.degraded is False, "one bad request is not an outage"

    health.record_failure("timeout")

    assert health.degraded is True
    assert health.cooldown_until > 0

    # A success clears the streak, so a recovered API is used again at once.
    health.cooldown_until = 0

    health.record_success()

    assert health.failures == 0
    assert health.degraded is False


def test_search_result_stamp_records_provenance():
    from search.search_result import SearchResult

    result = SearchResult(title="T", content="C", source="S", url="https://e.com/x")

    stamped = result.stamp(tool="brave")

    assert stamped is result, "stamp() annotates the result in place"
    assert stamped.tool == "brave"
    assert stamped.fetched_at, "evidence without a fetch time cannot be aged"
    assert stamped.domain == "e.com"
    assert result.published_at is None  # no publish date in the source: stay honest


def test_usability_rejects_placeholders_and_failures():
    from search.ranking import ranking
    from search.search_result import SearchResult

    assert ranking.is_usable(
        SearchResult(
            title="x",
            content="under development, no results",
            source="stub",
            url="",
            success=False,
        )
    ) is False

    assert ranking.is_usable(
        SearchResult(title="", content="", source="empty", url="")
    ) is False

    assert ranking.is_usable(
        SearchResult(
            title="Title",
            content="Tool not configured",
            source="stub",
            url="https://example.com/a",
        )
    ) is False

    assert ranking.is_usable(
        SearchResult(
            title="Title",
            content="A real paragraph of substance about the topic at hand.",
            source="Paper",
            url="https://example.com/b",
        )
    ) is True


def test_an_html_page_is_never_treated_as_a_feed():
    from tools.news import NewsTool

    assert NewsTool._looks_like_feed(
        "<?xml version='1.0'?><rss><channel><item/></channel></rss>"
    ) is True
    assert NewsTool._looks_like_feed("<feed><entry/></feed>") is True
    assert NewsTool._looks_like_feed("<!DOCTYPE html><html><body>News</body></html>") is False
    assert NewsTool._looks_like_feed("") is False


FEED_XML = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Launch scrubbed by weather</title>
            <description>The rocket was grounded.</description>
            <link>https://space.example/a</link>
            <pubDate>Mon, 01 Sep 2026 10:00:00 GMT</pubDate></item>
      <item><title>New telescope first light</title>
            <description>First images of a distant galaxy.</description>
            <link>https://space.example/b</link>
            <pubDate>Mon, 01 Sep 2026 09:00:00 GMT</pubDate></item>
    </channel></rss>"""


def test_the_fallback_parser_reads_real_items():
    """feedparser is optional; the fallback must still not invent anything."""
    from tools.news import NewsTool

    entries = NewsTool()._fallback_parse(FEED_XML)

    assert len(entries) == 2
    assert entries[0].title == "Launch scrubbed by weather"
    assert entries[0].link == "https://space.example/a"
    assert "2026" in entries[0].published


def test_the_fallback_parser_yields_nothing_for_non_feeds():
    from tools.news import NewsTool

    assert NewsTool()._fallback_parse("<html><body>news</body></html>") == []


def test_time_tool_refuses_questions_that_are_not_about_time():
    """A background refresh must not file a clock reading as some other answer."""
    from tools.time import TimeTool

    tool = TimeTool()

    assert asyncio.run(tool.execute("who is the prime minister of india")) == []


def test_weather_tool_says_so_when_it_cannot_find_the_place(monkeypatch):
    from tools import weather as weather_module

    async def no_place(self, text):
        return None

    monkeypatch.setattr(
        weather_module,
        "resolve_place",
        lambda *a, **k: asyncio.sleep(0, result=None),
        raising=False,
    )

    tool = weather_module.WeatherTool()

    async def broken_geocode(text):
        return None

    monkeypatch.setattr(tool, "_place", broken_geocode, raising=False)
    monkeypatch.setattr("tools._geo.geocode", broken_geocode, raising=False)

    assert asyncio.run(tool.execute("weather in atlantis")) == []


def test_tool_manager_ignores_unimplemented_tools():
    from tools.base import BaseTool
    from tools.manager import tool_manager

    unimplemented = [
        name
        for name, tool in tool_manager.tools.items()
        if not tool.implemented
    ]

    selected = {tool.name for tool in tool_manager.select(None)}

    for name in unimplemented:
        assert name not in selected
