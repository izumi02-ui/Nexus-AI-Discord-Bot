"""
Project Nexus

Discord Utilities

Output helpers for a bot whose text is partly generated from other people's
pages. Two things matter here: a reply must survive Discord's 2000-character
limit without cutting a code block in half, and a webpage that happens to
contain "@everyone" must not be able to make the bot ping the server.
"""

import re

MAX_LENGTH = 2000

#: Pings that a model could repeat verbatim from a scraped page.
_PING_RE = re.compile(r"@(?:everyone|here|role)", re.IGNORECASE)

#: Any user/role mention the model might have copied out of a search result.
_ID_MENTION_RE = re.compile(r"<@(?:!|&)?\d{5,20}>")


def safe_text(content: str) -> str:
    """
    Neutralise the Discord-side side effects of quoted text.

    Mentions are zero-width-escaped rather than deleted: "@everyone" inside a
    quoted headline is part of the answer, and silently removing it would
    corrupt what Nexus is reporting. It just must not notify anyone.
    """
    if not content:
        return ""

    content = _PING_RE.sub(lambda match: "@\u200b" + match.group(0)[1:], content)

    return _ID_MENTION_RE.sub(lambda match: match.group(0).replace("<", "<\u200b"), content)


def _fence_opener(chunk: str) -> str:
    """The ``` line that opened the block this chunk was cut inside of."""
    for line in reversed(chunk.splitlines()):
        if line.lstrip().startswith("```"):
            return line

    return "```"


def _split_point(content: str) -> int:
    """
    Where to break a long message: a paragraph boundary, then a newline, then
    a space - and never inside a ``` fence.
    """
    window = content[:MAX_LENGTH]

    fence = window.count("```")

    inside_code = fence % 2 == 1

    for needle in ("\n\n", "\n", " "):
        split = window.rfind(needle)

        if split > MAX_LENGTH * 0.4:
            if inside_code and needle != "\n":
                # Prefer breaking inside the block over closing it early.
                return split

            return split

    return MAX_LENGTH


async def send_long_message(
    destination,
    content: str,
):
    """Send to any object with ``send`` (channel, ctx, followup) or ``send_message``."""

    send = getattr(destination, "send", None) or getattr(
        destination,
        "send_message",
        None,
    )

    content = safe_text(str(content or ""))

    if not content.strip():
        return

    reopen = ""

    while len(content) > MAX_LENGTH:

        split = _split_point(content)

        chunk = (reopen + content[:split]).rstrip()

        content = content[split:].lstrip()

        if chunk.count("```") % 2:
            # Discord renders an unclosed fence as one giant code block that
            # also swallows the rest of the conversation, so the fence is
            # closed here and reopened on the next message.
            reopen = _fence_opener(chunk) + "\n"

            chunk = f"{chunk}\n```"

        else:
            reopen = ""

        await send(chunk)

    if content:
        await send((reopen + content).strip() or content)
