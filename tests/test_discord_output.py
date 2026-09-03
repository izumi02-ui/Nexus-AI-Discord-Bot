"""
Discord output safety: length limits, code fences, and quoted pings.
"""

import asyncio

from utils.discord_utils import MAX_LENGTH, safe_text, send_long_message


class Recorder:

    def __init__(self):
        self.sent = []

    async def send(self, content):
        self.sent.append(content)


def send(content):
    destination = Recorder()

    asyncio.run(send_long_message(destination, content))

    return destination.sent


def test_long_message_is_split_under_the_limit():
    parts = send("line\n" * 900)

    assert len(parts) > 1
    assert all(len(part) <= MAX_LENGTH for part in parts)
    assert "".join(parts).count("line") == 900


def test_a_split_code_block_is_reopened():
    content = "intro\n\n```python\n" + ("x = 1\n" * 400) + "```\n\noutro"

    parts = send(content)

    assert all(part.count("```") % 2 == 0 or part.endswith("```") for part in parts)


def test_everyone_ping_is_neutralised_not_deleted():
    out = safe_text("The headline said @everyone and <@123456789012345678>")

    assert "@everyone" not in out
    assert "everyone" in out
    assert "<@" not in out.replace("<@\u200b", "")


def test_the_safety_filter_applies_on_the_way_out():
    parts = send("The post says @everyone should read this. " * 100)

    assert "@everyone" not in "".join(parts)


def test_empty_and_whitespace_output_is_skipped():
    assert send("") == []
    assert send("   \n  ") == []


def test_short_message_is_one_part():
    assert send("hello") == ["hello"]
