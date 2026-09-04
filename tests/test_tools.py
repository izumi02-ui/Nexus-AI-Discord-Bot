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


def test_spotify_uses_form_oauth_and_plural_search_containers(monkeypatch):
    from tools import spotify as spotify_module

    calls = []

    async def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))

        if url.endswith("/api/token"):
            return {"access_token": "spotify-token", "expires_in": 3600}

        return {
            "tracks": {
                "items": [{
                    "id": "track-1",
                    "name": "Love Me",
                    "artists": [{"name": "Example Artist"}],
                    "album": {
                        "name": "Example Album",
                        "images": [{"url": "https://img.example/cover.jpg"}],
                    },
                    "external_urls": {"spotify": "https://open.spotify.com/track/1"},
                }]
            },
            "albums": {"items": []},
            "artists": {"items": []},
        }

    monkeypatch.setattr(spotify_module.settings, "spotify_client_id", "client")
    monkeypatch.setattr(spotify_module.settings, "spotify_client_secret", "secret")
    monkeypatch.setattr(spotify_module, "fetch_json", fake_fetch)
    spotify_module._TOKEN.update(value=None, expires_at=0.0)

    results = asyncio.run(spotify_module.SpotifyTool().execute("find Love Me song"))

    assert calls[0][1]["data_body"] == {"grant_type": "client_credentials"}
    assert "params" not in calls[0][1]
    assert calls[1][1]["params"]["type"] == "track,album,artist"
    assert calls[1][1]["params"]["q"] == "Love Me"
    assert results[0].title == "Track: Love Me"
    assert results[0].image == "https://img.example/cover.jpg"


def test_stackoverflow_fetches_real_answers_not_only_question_text(monkeypatch):
    from tools import stackoverflow as stackoverflow_module

    calls = []

    async def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))

        if url.endswith("/answers"):
            return {"items": [{
                "question_id": 42,
                "answer_id": 99,
                "body": "<p>Use <code>await task</code>.</p>",
                "score": 17,
                "is_accepted": True,
            }]}

        return {"items": [{
            "question_id": 42,
            "title": "How do I await a task?",
            "body": "<p>This is the question.</p>",
            "link": "https://stackoverflow.com/questions/42/example",
            "creation_date": 123,
            "score": 4,
            "answer_count": 2,
            "tags": ["python", "asyncio"],
            "view_count": 100,
        }]}

    monkeypatch.setattr(stackoverflow_module, "fetch_json", fake_fetch)

    results = asyncio.run(
        stackoverflow_module.StackOverflowTool().execute(
            "Python RuntimeError event loop is closed"
        )
    )

    assert calls[1][0].endswith("/questions/42/answers")
    assert "Accepted answer: Use await task ." in results[0].content
    assert results[0].metadata["is_accepted"] is True
    assert results[0].metadata["answer_id"] == 99


def test_duckduckgo_relative_image_is_safe_for_discord(monkeypatch):
    from tools import duckduckgo as duckduckgo_module

    async def fake_fetch(*args, **kwargs):
        return {
            "Heading": "Example",
            "AbstractText": "A useful factual summary.",
            "AbstractURL": "https://example.com",
            "Image": "/i/example.png",
        }

    monkeypatch.setattr(duckduckgo_module, "fetch_json", fake_fetch)

    result = asyncio.run(duckduckgo_module.DuckDuckGoTool().execute("Example"))[0]

    assert result.image == "https://duckduckgo.com/i/example.png"


def test_youtube_uses_official_search_and_video_endpoints(monkeypatch):
    from tools import youtube as youtube_module

    calls = []

    async def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))

        if url.endswith("/search"):
            return {"items": [{
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "Love Me — Official Video",
                    "description": "Official upload.",
                    "channelTitle": "Example Artist",
                    "publishedAt": "2026-09-01T10:00:00Z",
                    "thumbnails": {
                        "medium": {"url": "https://img.youtube.com/abc123.jpg"}
                    },
                },
            }]}

        return {"items": [{
            "id": "abc123",
            "statistics": {"viewCount": "1234", "likeCount": "100"},
            "contentDetails": {"duration": "PT3M20S"},
        }]}

    monkeypatch.setattr(youtube_module.settings, "youtube_api_key", "youtube-key")
    monkeypatch.setattr(youtube_module, "fetch_json", fake_fetch)

    results = asyncio.run(
        youtube_module.YouTubeTool().execute("Give me Love Me link from YouTube")
    )

    assert calls[0][0] == "https://www.googleapis.com/youtube/v3/search"
    assert calls[0][1]["params"]["key"] == "youtube-key"
    assert calls[0][1]["params"]["type"] == "video"
    assert calls[0][1]["params"]["q"] == "Love Me"
    assert calls[1][0] == "https://www.googleapis.com/youtube/v3/videos"
    assert results[0].url == "https://www.youtube.com/watch?v=abc123"
    assert results[0].thumbnail.endswith("abc123.jpg")
