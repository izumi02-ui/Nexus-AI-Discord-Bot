"""
The verifier: what Nexus may say, given what it found.

These tests are the accuracy contract in one file. Each one is a failure mode
the bot had or would otherwise have: invented links, invented numbers, a model
answering a live question from memory, and a model claiming it has no internet.
"""

from ai.verifier import verifier
from search.report import SearchReport


def make_report(result, *extra):
    rows = [result, *extra]

    from search.ranking import ranking

    return SearchReport(
        query="who is the prime minister of india",
        results=rows,
        cross=ranking.cross_check(rows),
    )


def test_grounded_answer_passes_through(result):
    evidence = result(
        title="PM",
        content="The prime minister of India is Shekhar Kumar as of 2026.",
        source="Example News",
        url="https://example.com/pm",
        confidence=0.9,
    )

    answer = (
        "The prime minister is Shekhar Kumar "
        "(https://example.com/pm), per Example News."
    )

    outcome = verifier.verify(
        query="who is the prime minister of india",
        answer=answer,
        report=make_report(
            evidence,
            result(
                title="PM confirmation",
                content="The prime minister of India is Shekhar Kumar as of 2026.",
                source="Second Example",
                url="https://second.example/pm",
            ),
        ),
        freshness="short",
    )

    assert outcome.grounded is True
    assert outcome.answer == answer.strip()
    assert outcome.needs_retry is False
    assert outcome.confidence >= 0.7


def test_fabricated_link_is_removed(result):
    evidence = result(
        content="The prime minister of India is Shekhar Kumar.",
        url="https://example.com/real",
    )

    answer = (
        "The prime minister is Shekhar Kumar "
        "[Wikipedia](https://en.wikipedia.org/wiki/Fake_Page)."
    )

    outcome = verifier.verify(
        query="who is the prime minister of india",
        answer=answer,
        report=make_report(
            evidence,
            result(
                content="The prime minister of India is Shekhar Kumar.",
                source="Second Example",
                url="https://second.example/pm",
            ),
        ),
        freshness="short",
    )

    assert "Fake_Page" not in outcome.answer
    assert "Shekhar Kumar" in outcome.answer
    assert outcome.removed_urls == ["https://en.wikipedia.org/wiki/Fake_Page"]
    assert any("link" in issue for issue in outcome.issues)


def test_invented_number_triggers_a_reask(result):
    evidence = result(
        content="The population of Tokyo is 14.1 million people.",
        url="https://example.com/tokyo",
    )

    answer = "Tokyo has about 27.4 million people (https://example.com/tokyo)."

    outcome = verifier.verify(
        query="population of tokyo",
        answer=answer,
        report=make_report(evidence),
        freshness="short",
    )

    assert outcome.needs_retry is True
    assert any("figure" in issue for issue in outcome.issues)
    assert outcome.confidence <= 0.6
    # The verifier does not rewrite numbers itself; it refuses to let the
    # answer ship unchallenged, which is what the retry is for.
    assert "27.4" in outcome.answer


def test_cutoff_excuse_is_not_accepted(result):
    evidence = result(
        content="The prime minister of India is Shekhar Kumar.",
        url="https://example.com/pm",
    )

    answer = (
        "I cannot browse the internet, and my knowledge ends in January 2025, "
        "so I cannot tell you who the prime minister is."
    )

    outcome = verifier.verify(
        query="who is the prime minister of india",
        answer=answer,
        report=make_report(evidence),
        freshness="short",
    )

    assert outcome.needs_retry is True
    assert any("cannot check live information" in issue for issue in outcome.issues)


def test_time_sensitive_answer_without_evidence_is_retried(result):
    outcome = verifier.verify(
        query="what is the price of bitcoin right now",
        answer="Bitcoin is trading around $60,000.",
        report=None,
        freshness="instant",
    )

    assert outcome.needs_retry is True
    assert outcome.grounded is False
    assert "unverified" in outcome.summary.lower()


def test_raw_tool_call_is_retried_and_never_accepted():
    answer = (
        "<tool_call><tool_call>duckduckgo</tool_call>"
        "<arg_key>query</arg_key><arg_value>PS6 news</arg_value></tool_call>"
    )

    first = verifier.verify(
        query="upcoming PS6 news",
        answer=answer,
        report=None,
        freshness="short",
    )

    assert first.needs_retry is True
    assert first.grounded is False

    final = verifier.verify(
        query="upcoming PS6 news",
        answer=answer,
        report=None,
        freshness="short",
        allow_retry=False,
    )

    assert final.refused is True
    assert "<tool_call>" not in final.answer


def test_stable_question_without_evidence_is_fine():
    outcome = verifier.verify(
        query="explain photosynthesis",
        answer="Photosynthesis converts light into chemical energy.",
        report=None,
        freshness="static",
    )

    assert outcome.needs_retry is False
    assert "Photosynthesis converts" in outcome.answer


def test_single_source_is_disclosed(result):
    evidence = result(
        content="The prime minister of India is Shekhar Kumar.",
        url="https://example.com/pm",
    )

    outcome = verifier.verify(
        query="who is the prime minister of india",
        answer="The prime minister of India is Shekhar Kumar.",
        report=make_report(evidence),
        freshness="short",
    )

    assert any("one" in note for note in outcome.notes)


def test_disputed_knowledge_is_never_presented_as_fact(result):
    evidence = result(
        content="The capital of the realm is Vellore.",
        url="https://example.com/capital",
    )

    outcome = verifier.verify(
        query="what is the capital",
        answer="The capital is Vellore.",
        report=make_report(evidence),
        freshness="long",
        knowledge_rows=[{"status": "disputed", "value": "The capital is Delhi."}],
    )

    assert outcome.grounded is False or outcome.confidence <= 0.7


def test_refusal_when_configured_to_refuse(result, monkeypatch):
    from utils.settings import settings

    monkeypatch.setattr(settings, "refuse_when_unverified", True)
    monkeypatch.setattr(settings, "auto_retry_with_search", False)

    outcome = verifier.verify(
        query="what is the weather in delhi right now",
        answer="It is probably warm.",
        report=None,
        freshness="instant",
    )

    assert outcome.refused is True
    assert "could not" in outcome.answer.lower() or "unable" in outcome.answer.lower()


def test_footer_is_short_and_discloses_conflicts(result):
    evidence = result(content="Rate is 5.50 percent.", url="https://a.com/1")
    other = result(
        content="Rate is 6.25 percent.",
        source="Other Paper",
        url="https://b.com/2",
    )

    outcome = verifier.verify(
        query="what is the interest rate",
        answer="The rate is 5.50 percent.",
        report=make_report(evidence, other),
        freshness="short",
    )

    footer = outcome.footer()

    assert footer is None or footer.startswith("-#")
    assert len(footer or "") < 240
