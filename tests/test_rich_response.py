"""Conditional Discord presentation contracts."""

import asyncio
from types import SimpleNamespace

from search.report import SearchReport
from search.search_result import SearchResult
from utils.rich_response import (
    code_blocks,
    presentation_kind,
    reference_image,
    send_ai_response,
)


class Recorder:
    def __init__(self):
        self.sent = []

    async def send(self, *args, **kwargs):
        self.sent.append((args, kwargs))


USER = SimpleNamespace(
    id=123456789,
    display_name="Test Display",
    name="test_username",
)


def test_normal_chat_stays_plain():
    assert presentation_kind("hello", "Hey!", {"presentation": "plain"}) == "plain"


def test_explanation_uses_reference_embed():
    assert presentation_kind(
        "explain black holes",
        "A sufficiently detailed explanation " * 20,
        {"presentation": "reference"},
    ) == "reference"


def test_code_always_uses_code_embed():
    answer = "bot.py\n```python\nprint('ready')\n```"

    assert presentation_kind("create a bot", answer, {}) == "code"
    assert code_blocks(answer) == [("python", "print('ready')")]


def test_code_request_refusal_is_not_labelled_as_generated_code():
    refusal = "I could not verify that right now, so I would rather not guess."

    assert presentation_kind("make Python code", refusal, {}) == "plain"


def test_reference_image_only_uses_source_metadata():
    report = SearchReport(
        query="black holes",
        results=[
            SearchResult(
                title="Black hole",
                content="Reference content",
                source="Wikipedia",
                url="https://en.wikipedia.org/wiki/Black_hole",
                thumbnail="https://upload.wikimedia.org/example.jpg",
            )
        ],
    )

    assert reference_image(report) == "https://upload.wikimedia.org/example.jpg"


def test_short_code_is_sent_inside_an_embed():
    destination = Recorder()
    outcome = {
        "query": "create python code",
        "raw": "```python\nprint('ready')\n```",
        "response": "unused",
        "route": {"presentation": "plain"},
    }

    kind = asyncio.run(send_ai_response(destination, outcome, USER))

    assert kind == "code"
    assert len(destination.sent) == 3
    assert destination.sent[0][0] == ("Here is the requested implementation:",)
    embed = destination.sent[1][1]["embed"]
    assert "print('ready')" in embed.description
    assert embed.title == "Generated Code"
    assert embed.footer.text is None
    footer = destination.sent[2][0][0]
    assert "Requested by **Test Display**" in footer
    assert "@test\\_username" in footer
    assert "ID `123456789`" in footer


def test_reference_answer_has_image_sources_and_verification():
    destination = Recorder()
    result = SearchResult(
        title="Black hole",
        content="Reference content",
        source="Wikipedia",
        url="https://en.wikipedia.org/wiki/Black_hole",
        thumbnail="https://upload.wikimedia.org/example.jpg",
    )
    outcome = {
        "query": "explain black holes",
        "raw": "Black holes are regions where gravity strongly affects spacetime.",
        "response": "unused",
        "route": {"presentation": "reference"},
        "report": SearchReport(query="black holes", results=[result]),
        "verification": SimpleNamespace(summary="verified · confidence 0.90"),
    }

    kind = asyncio.run(send_ai_response(destination, outcome, USER))

    assert kind == "reference"
    assert destination.sent[0][0] == ("Here’s a structured breakdown.",)
    embed = destination.sent[1][1]["embed"]
    assert embed.image.url == "https://upload.wikimedia.org/example.jpg"
    assert any(field.name == "Verification" for field in embed.fields)
    assert embed.footer.text is None
    links = destination.sent[2][1]["embed"]
    assert links.title == "Links & References"
    assert links.thumbnail.url == "https://upload.wikimedia.org/example.jpg"
    assert "Open link" in links.fields[0].value
    assert "Requested by **Test Display**" in destination.sent[3][0][0]


def test_math_solution_uses_plain_embed_plain_flow():
    destination = Recorder()
    outcome = {
        "query": "solve this calculus equation",
        "raw": (
            "I’ll use the power rule.\n\n"
            "1. Differentiate each term.\n2. Combine the results.\n\n"
            "So the derivative follows directly from the rule."
        ),
        "response": "unused",
        "route": {"presentation": "solution"},
    }

    kind = asyncio.run(send_ai_response(destination, outcome, USER))

    assert kind == "solution"
    assert destination.sent[0][0] == ("I’ll use the power rule.",)
    embed = destination.sent[1][1]["embed"]
    assert embed.title == "Worked Solution"
    assert "Differentiate each term" in embed.description
    assert embed.footer.text is None
    assert "derivative follows" in destination.sent[2][0][0]
    assert "Requested by **Test Display**" in destination.sent[2][0][0]


def test_plain_spotify_result_always_sends_real_link_and_cover_embed():
    destination = Recorder()
    result = SearchResult(
        title="Track: Love Me",
        content="Track Love Me by Example Artist, from Example Album.",
        source="Spotify",
        url="https://open.spotify.com/track/example",
        image="https://i.scdn.co/image/example-cover",
    )
    outcome = {
        "query": "give me Love Me song link from Spotify",
        "raw": "I found the matching track.",
        "response": "legacy response with plain sources",
        "route": {"presentation": "plain"},
        "report": SearchReport(query="Love Me", results=[result]),
    }

    kind = asyncio.run(send_ai_response(destination, outcome, USER))

    assert kind == "plain"
    assert destination.sent[0][0] == ("I found the matching track.",)
    embed = destination.sent[1][1]["embed"]
    assert embed.title == "Links & References"
    assert embed.thumbnail.url == "https://i.scdn.co/image/example-cover"
    assert "https://open.spotify.com/track/example" in embed.fields[0].value
    assert "legacy response" not in str(destination.sent)


def test_more_than_three_links_stay_in_one_captioned_embed():
    destination = Recorder()
    results = [
        SearchResult(
            title=f"Result {index}",
            content=f"Caption for result {index}.",
            source="Search",
            url=f"https://example.com/{index}",
        )
        for index in range(1, 6)
    ]
    outcome = {
        "query": "find useful references",
        "raw": "I found five useful references.",
        "response": "unused",
        "route": {"presentation": "plain"},
        "report": SearchReport(query="references", results=results),
    }

    asyncio.run(send_ai_response(destination, outcome, USER))

    embeds = [kwargs["embed"] for _, kwargs in destination.sent if "embed" in kwargs]
    assert len(embeds) == 1
    assert len(embeds[0].fields) == 5
    assert all("Caption for result" in field.value for field in embeds[0].fields)
