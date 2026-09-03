"""
Project Nexus

Freshness

How current does information need to be before Nexus is allowed to say it
out loud?

Different questions rot at different speeds. A weather report is worthless
after a couple of hours, a country's population is fine for months, and the
plot of a 1994 film never expires. This module turns a query into a
freshness budget (in seconds) which the cache, the ranker and the answer
verifier all respect.
"""

import math
import re

from search.query import normalize_query, tokens
from utils.time_utils import DAY, HOUR, MINUTE, YEAR

# "instant" means: answer from the tools, never from memory, and keep the
# cache alive for only a few minutes.
INSTANT = 5 * MINUTE
SHORT = 6 * HOUR
MEDIUM = 3 * DAY
LONG = 30 * DAY
ETERNAL = 10 * YEAR

_BUDGETS = {
    "instant": INSTANT,
    "short": SHORT,
    "medium": MEDIUM,
    "long": LONG,
    "static": ETERNAL,
}

_INSTANT_TRIGGERS = (
    r"\bweather\b",
    r"\b(temperature|forecast|rain|snow|humidit|wind speed|air quality)\b",
    r"\b(earthquake|volcano eruption|wildfire|flood)\b",
    r"\bscore(s|line)?\b",
    r"\b(right now|at this moment|at the moment|today's|tonight's|live score)\b",
    r"\b(?:currently|now)\s+(?:playing|streaming|airing|showing)\b",
    r"\b(gold|silver|bitcoin|btc|eth|ethereum|crypto|stock|shares|nifty|sensex)\b",
    r"\bprice(s)?\b",
    r"\b(exchange rate|convert|conversion|currency)\b",
    r"\b\d+(?:\.\d+)?\s*(usd|eur|gbp|inr|jpy|aud|cad|chf|sgd|aed|zar)\b",
    r"\b(usd|eur|gbp|inr|jpy)\s+(?:to|into)\s+\w+\b",
    r"\b(promotion|in stock|availability)\b",
    r"\btraffic\b",
    # A clock or calendar question is the most perishable thing there is.
    r"\b(current time|time is it|time in|what time|local time|time zone|timezone)\b",
    r"\b(today'?s date|what date|date is it|day of the week)\b",
    r"\b(is it|are we)\b.*\b(daylight saving|summer time)\b",
)

_SHORT_TRIGGERS = (
    r"\b(today|tonight|yesterday|latest|breaking|current|currently|now)\b",
    r"\bthis (week|month|year|season|semester)\b",
    r"\bnews\b",
    r"\b(update|updates|changelog|patch notes)\b",
    r"\blast (night|week|month|weekend|game|match|episode)\b",
    r"\b(this morning|so far|at the moment)\b",
    # "best X in 2026" is a question about the present wearing a year's clothes.
    r"\b(?:in|for|as of|since)\s+20\d\d\b",
    r"\b(?:release|released|launch|launched|come out|out)\b[^?]{0,30}\b(yet|now|already)\b",
    r"\brecent(ly)?\b",
    r"\b(trending|viral)\b",
    r"\bstill (available|true|open|working|out|alive|active|maintained|supported)\b",
    r"\b(any new|new (episode|movie|album|phone|model|version|release))\b",
    r"\b(upcoming)\b",
    r"\b(prime minister|president|ceo|founder|owner|mayor|governor|chancellor|pope)\b",
    r"\b(ranked?|ranking|standings|points table|leaderboard)\b",
    r"\b(war|election|vote|verdict|sentenced|strike|crash|outage)\b",
    r"\b(open|closed|operating hours)\b",
    r"\b(20\d\d)\b\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
)

_MEDIUM_TRIGGERS = (
    r"\bpopulation\b",
    r"\b(gdp|inflation|unemployment|cpi)\b",
    r"\b(release date|released|launched|announced)\b",
    r"\b(benchmark|benchmarks|review|specs|specifications)\b",
    r"\b(vs|versus|compare|comparison|better than)\b",
    r"\b(who won|winner|won the|record for)\b",
    r"\b(api|sdk|library|framework|model)\b.*\b(version|v\d+)\b",
    r"\b(version|update)\s*\d+",
    r"\bhow (many|much)\b",
    r"\b(how many people|population of)\b",
    r"\b(best|top \d|most popular)\b",
    r"\b(compared to|compared with|difference between)\b",
    r"\b(is|are|does|do|can|will)\b.*\b(yet|anymore|still|now)\b",
    r"\b(released yet|coming out|out now|available now)\b",
)

_LONG_TRIGGERS = (
    r"\b(census|according to|official statistics)\b",
    r"\b(highest|largest|smallest|fastest|tallest|richest|most expensive)\b",
    r"\b(capital of|currency of|population of|area of)\b",
)

# Pure reasoning or stable knowledge: no tools needed and nothing to go stale.
_STATIC_TRIGGERS = (
    r"^(hi|hello|hey|yo|sup|thanks|thank you|good morning|good afternoon|good evening)\b",
    r"\b(write|generate|implement|refactor|debug|explain|summarise|summarize)\b\s+(?:me\s+)?(?:a\s+|some\s+|the\s+)?(?:python|code|function|script|program|regex|sql)\b",
    r"\b(definition of|meaning of|synonym|antonym|rhyme)\b",
    r"\b(calculate|compute|solve|simplify)\b",
    r"\d\s*[-+*/^%]\s*\d",
    r"\b(who are you|what are you|your name|who made you|who created you)\b",
    r"\b(joke|haiku|poem|story|roleplay|motivat)\b",
)


def classify(query: str) -> str:
    """
    Bucket a query into instant / short / medium / long / static.
    """
    text = normalize_query(query) or (query or "").lower().strip()

    if not text:
        return "static"

    urgent = any(
        re.search(pattern, text)
        for pattern in _INSTANT_TRIGGERS + _SHORT_TRIGGERS
    )

    if not urgent:
        for pattern in _STATIC_TRIGGERS:
            if re.search(pattern, text):
                return "static"

    for pattern in _INSTANT_TRIGGERS:
        if re.search(pattern, text):
            return "instant"

    for pattern in _SHORT_TRIGGERS:
        if re.search(pattern, text):
            return "short"

    for pattern in _MEDIUM_TRIGGERS:
        if re.search(pattern, text):
            return "medium"

    for pattern in _LONG_TRIGGERS:
        if re.search(pattern, text):
            return "long"

    # Nothing time-sensitive was detected. Searching anyway would cost time
    # and money without making the answer better, so the model answers.
    return "static"


def budget_for(query: str) -> int:
    """
    Maximum age, in seconds, of information that may be repeated as current.
    """
    return _BUDGETS.get(classify(query), MEDIUM)


#: Older call sites use the short name.
budget = budget_for


def label(query: str) -> str:
    """Human readable description of the freshness requirement."""
    return {
        "instant": "must be minutes old",
        "short": "within the last few hours",
        "medium": "within the last few days",
        "long": "within the last month",
        "static": "not time sensitive",
    }.get(classify(query), "unknown")


def needs_fresh_evidence(query: str) -> bool:
    """True when answering from parametric memory alone is not acceptable."""
    return classify(query) in {"instant", "short"}


def confidence_from_age(age_seconds: float | None, budget_seconds: int) -> float:
    """
    Multiplier applied to a source's confidence as it ages.

    Fresh results keep their score. Results past the budget decay smoothly
    towards 35% - still useful background, never a claim about "now". An
    unknown date is scored as mostly-fresh: a missing timestamp should not be
    a free pass, but it should not disqualify a source either.
    """
    if budget_seconds <= 0:
        return 1.0

    if age_seconds is None:
        return 0.72

    if age_seconds <= budget_seconds:
        return 1.0

    overshoot = (age_seconds - budget_seconds) / max(budget_seconds, MINUTE)

    return 0.35 + 0.65 * math.exp(-overshoot * 0.55)


def is_answerable_from_memory(query: str) -> bool:
    """
    Static, well-known questions may be answered without tools; anything
    else should be checked first.
    """
    if classify(query) == "static":
        return True

    words = tokens(query)

    return bool(words) and len(words) <= 2
