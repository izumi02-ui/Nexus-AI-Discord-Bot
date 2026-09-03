"""
Project Nexus

Time Utilities

Single source of truth for "now", date parsing and staleness math.

Nexus has to answer questions such as "what is the current price of ...",
"who won yesterday?" or "is this still true?". Every one of those answers
depends on knowing how old a piece of information is, so the whole bot uses
the helpers below instead of scattering ``datetime`` calls around.
"""

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

UTC = timezone.utc

INDIA_TIMEZONE = timezone(
    timedelta(hours=5, minutes=30),
    name="IST",
)

# One hour / day / week / month / year, in seconds.
MINUTE = 60
HOUR = 3600
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY
YEAR = 365 * DAY

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11,
    "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}

_RELATIVE_UNITS = {
    "second": 1,
    "sec": 1,
    "minute": MINUTE,
    "min": MINUTE,
    "hour": HOUR,
    "hr": HOUR,
    "day": DAY,
    "week": WEEK,
    "month": MONTH,
    "year": YEAR,
}

_RELATIVE_RE = re.compile(
    r"(?P<count>\d+)\s*(?P<unit>"
    + "|".join(sorted(_RELATIVE_UNITS, key=len, reverse=True))
    + r")s?\s+ago",
    re.IGNORECASE,
)

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_MDY_RE = re.compile(
    r"(?P<month>[A-Za-z]{3,9})\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+"
    r"(?P<year>\d{4})",
)
_DMY_RE = re.compile(
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>[A-Za-z]{3,9})\.?,?\s+"
    r"(?P<year>\d{4})",
)
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")


# ==========================================
# Clock
# ==========================================

def now_utc() -> datetime:
    """Timezone aware "now" in UTC."""
    return datetime.now(UTC)


def now_india() -> datetime:
    """Timezone aware "now" in India Standard Time."""
    return now_utc().astimezone(INDIA_TIMEZONE)


def to_utc(value: datetime) -> datetime:
    """Normalise any datetime into an aware UTC datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


# ==========================================
# Parsing
# ==========================================

def parse_datetime(value) -> datetime | None:
    """
    Best effort parsing of anything a search provider or a human throws at us.

    Understands ISO strings, RFC-2822 (RSS/Atom feeds), unix timestamps,
    "3 days ago" style text and plain human dates. Returns an aware UTC
    datetime, or None when the value carries no usable date.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return to_utc(value)

    if isinstance(value, (int, float)):
        try:
            return to_utc(datetime.fromtimestamp(float(value), UTC))
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip()

    if not text or text.lower() in {"none", "null", "unknown", "n/a", "-"}:
        return None

    # ISO-8601 (also covers SQLite CURRENT_TIMESTAMP values).
    if _ISO_RE.match(text):
        try:
            return to_utc(
                datetime.fromisoformat(text.replace("Z", "+00:00"))
            )
        except ValueError:
            pass

    # "2026-07-07T12:00" or feed dates such as
    # "Mon, 07 Jul 2026 09:00:00 GMT".
    try:
        return to_utc(parsedate_to_datetime(text))
    except (TypeError, ValueError):
        pass

    # Relative: "3 hours ago", "1 day ago".
    relative = _RELATIVE_RE.search(text)

    if relative:
        seconds = int(relative.group("count")) * _RELATIVE_UNITS[
            relative.group("unit").lower()
        ]
        return now_utc() - timedelta(seconds=seconds)

    # Human: "July 7, 2026" / "7 July 2026".
    for pattern, order in ((_MDY_RE, "mdy"), (_DMY_RE, "dmy")):
        match = pattern.search(text)

        if not match:
            continue

        month = _MONTHS.get(match.group("month").lower()[:9])

        if month is None:
            month = _MONTHS.get(match.group("month").lower()[:3])

        if month is None:
            continue

        try:
            return to_utc(
                datetime(
                    int(match.group("year")),
                    month,
                    int(match.group("day")),
                )
            )
        except ValueError:
            continue

    # Bare year, e.g. "2024" or "March 2024" -> assume 1st of that period.
    years = _YEAR_RE.findall(text)

    if years:
        lowered = text.lower()

        for name, number in _MONTHS.items():
            if name in lowered:
                try:
                    return to_utc(datetime(int(years[-1]), number, 1))
                except ValueError:
                    break

        try:
            return to_utc(datetime(int(years[-1]), 1, 1))
        except ValueError:
            return None

    return None


def iso(value: datetime | None) -> str | None:
    """Serialise a datetime to ISO-8601 UTC text (SQLite friendly)."""
    if value is None:
        return None

    return to_utc(value).replace(microsecond=0).isoformat()


# ==========================================
# Staleness maths
# ==========================================

def age_seconds(value, reference: datetime | None = None) -> float | None:
    """
    How old a timestamp is, in seconds.

    Returns None when no date could be parsed, which callers treat as
    "unknown age" rather than "fresh".
    """
    parsed = parse_datetime(value)

    if parsed is None:
        return None

    delta = (reference or now_utc()) - parsed

    return max(0.0, delta.total_seconds())


def humanize_age(value, reference: datetime | None = None) -> str:
    """Render an age the way a human would say it: '3 hours ago'."""
    seconds = age_seconds(value, reference)

    if seconds is None:
        return "unknown age"

    if seconds < 45:
        return "just now"

    for name, size in (
        ("year", YEAR),
        ("month", MONTH),
        ("week", WEEK),
        ("day", DAY),
        ("hour", HOUR),
        ("minute", MINUTE),
    ):
        if seconds >= size:
            count = int(seconds // size)
            return f"{count} {name}{'' if count == 1 else 's'} ago"

    return "just now"


def is_expired(value, ttl_seconds: float | None) -> bool:
    """True when a timestamp is older than the supplied lifetime."""
    if ttl_seconds is None:
        return False

    age = age_seconds(value)

    if age is None:
        # Unknown age is treated as stale: Nexus would rather re-check than
        # repeat something it cannot vouch for.
        return True

    return age > ttl_seconds
