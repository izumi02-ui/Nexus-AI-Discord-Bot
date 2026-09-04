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

    tool = weather_module.WeatherTool()

    async def broken_geocode(text):
        return None

    monkeypatch.setattr(weather_module, "geocode", broken_geocode)

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


def test_gnews_uses_v4_api_and_survives_newsapi_failure(monkeypatch):
    from tools import news as news_module
    from tools._http import FetchError

    calls = []

    async def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))

        if "newsapi.org" in url:
            raise FetchError("quota exhausted")

        return {
            "articles": [
                {
                    "title": "Verified launch update",
                    "description": "The launch occurred after a weather delay.",
                    "url": "https://publisher.example/launch",
                    "image": "https://publisher.example/launch.jpg",
                    "publishedAt": "2026-09-04T08:00:00Z",
                    "source": {
                        "name": "Example Publisher",
                        "url": "https://publisher.example",
                    },
                }
            ]
        }

    monkeypatch.setattr(news_module.settings, "news_api_key", "news-key")
    monkeypatch.setattr(news_module.settings, "gnews_api_key", "gnews-key")
    monkeypatch.setattr(news_module, "fetch_json", fake_fetch)

    results = asyncio.run(
        news_module.NewsTool()._from_api("latest launch news", ["launch"])
    )

    assert [call[0] for call in calls] == [
        "https://newsapi.org/v2/everything",
        "https://gnews.io/api/v4/search",
    ]
    assert calls[1][1]["params"]["apikey"] == "gnews-key"
    assert results[0].source == "Example Publisher"
    assert results[0].image.endswith("launch.jpg")


def test_reddit_requires_all_approved_oauth_settings(monkeypatch):
    from tools import reddit as reddit_module

    monkeypatch.setattr(reddit_module.settings, "reddit_client_id", "")
    monkeypatch.setattr(reddit_module.settings, "reddit_client_secret", "")
    monkeypatch.setattr(reddit_module.settings, "reddit_user_agent", "")

    assert reddit_module.RedditTool().available is False


def test_reddit_uses_oauth_and_reuses_its_token(monkeypatch):
    from tools import reddit as reddit_module

    calls = []

    async def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))

        if url.endswith("/api/v1/access_token"):
            return {"access_token": "approved-token", "expires_in": 3600}

        return {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "A useful community report",
                            "selftext": "Users describe their experience.",
                            "permalink": "/r/python/comments/example/report/",
                            "subreddit": "python",
                            "created_utc": 1788512400,
                            "author": "example_user",
                            "score": 42,
                            "num_comments": 7,
                            "upvote_ratio": 0.9,
                        }
                    }
                ]
            }
        }

    monkeypatch.setattr(reddit_module.settings, "reddit_client_id", "client")
    monkeypatch.setattr(reddit_module.settings, "reddit_client_secret", "secret")
    monkeypatch.setattr(
        reddit_module.settings,
        "reddit_user_agent",
        "ProjectNexus/2.0 by u/example",
    )
    monkeypatch.setattr(reddit_module, "fetch_json", fake_fetch)

    tool = reddit_module.RedditTool()
    first = asyncio.run(tool.execute("search reddit r/python async discord"))
    second = asyncio.run(tool.execute("search reddit r/python async discord"))

    assert calls[0][0] == "https://www.reddit.com/api/v1/access_token"
    assert calls[0][1]["data_body"] == {"grant_type": "client_credentials"}
    assert calls[1][0] == "https://oauth.reddit.com/r/python/search"
    assert calls[1][1]["headers"]["Authorization"] == "Bearer approved-token"
    assert sum(url.endswith("/api/v1/access_token") for url, _ in calls) == 1
    assert first[0].source == "Reddit"
    assert second[0].metadata["comments"] == 7
