"""Small, dependency-free helpers shared by the media cogs."""

from __future__ import annotations

import html
import re


URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
MARKDOWN_RE = re.compile(r"[*_~`>#|]+")
TIME_PART_RE = re.compile(
    r"^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?$",
    re.IGNORECASE,
)


def format_duration(milliseconds: int | float | None, *, stream: bool = False) -> str:
    """Return a compact player duration such as ``1:04:09``."""
    if stream:
        return "LIVE"

    total = max(0, int((milliseconds or 0) / 1000))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes}:{seconds:02d}"


def parse_timecode(value: str) -> int:
    """Parse ``90``, ``1:30``, ``1:02:03`` or ``1h2m3s`` to milliseconds."""
    text = (value or "").strip().lower().replace(" ", "")

    if not text:
        raise ValueError("time is empty")

    if text.isdigit():
        seconds = int(text)
    elif ":" in text:
        parts = text.split(":")

        if len(parts) not in {2, 3} or any(not part.isdigit() for part in parts):
            raise ValueError("use seconds, MM:SS, HH:MM:SS, or 1h2m3s")

        numbers = [int(part) for part in parts]

        if len(numbers) == 2:
            minutes, final_seconds = numbers
            seconds = minutes * 60 + final_seconds
        else:
            hours, minutes, final_seconds = numbers
            seconds = hours * 3600 + minutes * 60 + final_seconds
    else:
        match = TIME_PART_RE.fullmatch(text)

        if not match or not any(match.groupdict().values()):
            raise ValueError("use seconds, MM:SS, HH:MM:SS, or 1h2m3s")

        seconds = (
            int(match.group("hours") or 0) * 3600
            + int(match.group("minutes") or 0) * 60
            + int(match.group("seconds") or 0)
        )

    if seconds < 0 or seconds > 24 * 3600:
        raise ValueError("time must be between 0 seconds and 24 hours")

    return seconds * 1000


def truncate(text: str, limit: int) -> str:
    clean = " ".join((text or "").split())

    if len(clean) <= limit:
        return clean

    return clean[: max(1, limit - 1)].rstrip() + "…"


def markdown_link(label: str, url: str | None) -> str:
    """Build a safe Discord link without allowing label markup injection."""
    title = truncate(label, 90).replace("[", "(").replace("]", ")")

    if url and url.startswith(("https://", "http://")):
        return f"[{title}]({url})"

    return title


def speakable_text(text: str, *, limit: int = 900) -> str:
    """Turn a formatted Nexus answer into natural text for TTS."""
    clean = html.unescape(text or "")
    clean = CODE_BLOCK_RE.sub(
        " I put the code in the text channel so it is easy to copy. ", clean
    )
    clean = URL_RE.sub(" the linked source ", clean)
    clean = MARKDOWN_RE.sub("", clean)
    clean = re.sub(r"^Requested by .*?$", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"\s+", " ", clean).strip()

    if not clean:
        return "I posted the details in the text channel."

    return truncate(clean, limit)
