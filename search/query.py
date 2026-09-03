"""
Project Nexus

Query Helpers

Shared text normalisation for search, caching, ranking and the knowledge
base. Everything that compares two questions uses these helpers so that
"what is the population of japan?" and "What is the population of Japan"
end up being the same query.
"""

import hashlib
import re
from urllib.parse import urlparse

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "i", "you", "he", "she",
    "it", "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "its", "our", "their", "of", "in", "on", "at", "to", "for",
    "with", "about", "into", "from", "by", "as", "and", "or", "but", "if",
    "so", "than", "then", "that", "this", "these", "those", "there",
    "here", "what", "which", "who", "whom", "whose", "when", "where",
    "why", "how", "not", "no", "yes", "can", "could", "would", "should",
    "will", "shall", "may", "might", "must", "please", "tell", "me",
    "give", "know", "think", "just", "some", "any", "more", "most", "much",
    "many", "very", "really", "also", "well", "get", "got", "make", "made",
}

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.+-]*")
_SPACE_RE = re.compile(r"\s+")
_PUNCT_TAIL_RE = re.compile(r"[\s?!.:,;]+$")

# Prefixes users attach to a question that are not part of the question.
_COMMAND_PREFIX_RE = re.compile(
    r"^(?:hey|ok|okay|yo|nexus|bot|please|pls|can you|could you|would you)\b[,\s]*",
    re.IGNORECASE,
)

_SEARCH_VERB_RE = re.compile(
    r"^(?:search(?:\s+for)?|look\s?up|google|find|check|research|"
    r"tell me|what'?s|what is|who is|when did|when is)\b[,\s]*",
    re.IGNORECASE,
)


def normalize_query(query: str) -> str:
    """
    Canonical form of a user query.

    Keeps word order and content (order matters for "Spider-Man 3 vs 4")
    while dropping case, command prefixes and trailing punctuation.
    """
    if not query:
        return ""

    text = " ".join(query.strip().lower().split())

    # Discord ping / slash style leftovers.
    text = re.sub(r"<@!?\d+>", " ", text)
    text = _COMMAND_PREFIX_RE.sub("", text)
    text = _SEARCH_VERB_RE.sub("", text)
    text = _PUNCT_TAIL_RE.sub("", text)

    return _SPACE_RE.sub(" ", text).strip(" ?!.")


def tokens(query: str, *, keep_stopwords: bool = False) -> list[str]:
    """Meaningful words of a query."""
    words = _WORD_RE.findall((query or "").lower())

    if keep_stopwords:
        return words

    return [word for word in words if not keep_stopwords and word not in STOPWORDS]


def content_signature(query: str) -> str:
    """Order-insensitive fingerprint used to spot re-asks of the same thing."""
    return "|".join(sorted(set(tokens(query)))) or "empty"


def cache_key(query: str, tools=None) -> str:
    """Stable cache key for a query plus the set of providers used."""
    normalized = normalize_query(query) or (query or "").strip().lower()
    providers = ",".join(sorted(set(tools))) if tools else "any"

    raw = f"{normalized}::{providers}"

    return hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:24]


def topic_of(query: str, limit: int = 8) -> str:
    """
    Short topic label for a query, used by the knowledge base watchlist.
    """
    words = tokens(query)

    if not words:
        words = _WORD_RE.findall((query or "").lower())

    return " ".join(words[:limit]).strip() or (query or "").strip().lower()[:limit * 4]


def domain_of(url: str | None) -> str:
    """ registrable-ish domain of a URL: 'en.wikipedia.org' -> 'wikipedia.org'."""
    if not url:
        return ""

    host = urlparse(url).netloc.lower()

    if "@" in host:
        host = host.split("@")[-1]

    host = host.split(":")[0]

    parts = host.split(".")

    if len(parts) >= 3 and parts[-2] in {
        "co", "com", "org", "net", "gov", "edu", "ac", "govt"
    }:
        return ".".join(parts[-3:])

    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def overlap(first: str, second: str) -> float:
    """Fraction of shared content words between two queries (0.0 - 1.0)."""
    a = set(tokens(first))
    b = set(tokens(second))

    if not a or not b:
        return 0.0

    return len(a & b) / max(1, min(len(a), len(b)))


def similarity(first: str, second: str) -> float:
    """Cheap text similarity ratio, used for duplicate detection."""
    a = " ".join(normalize_query(first).split())
    b = " ".join(normalize_query(second).split())

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    if len(a) > 900:
        a = a[:900]
    if len(b) > 900:
        b = b[:900]

    from difflib import SequenceMatcher

    return SequenceMatcher(None, a, b, autojunk=True).ratio()


def truncate_words(text: str, limit: int = 1200) -> str:
    """Trim text on a word boundary so quoted evidence never cuts mid-token."""
    text = " ".join((text or "").split())

    if len(text) <= limit:
        return text

    cut = text.rfind(" ", 0, limit)

    if cut < limit // 2:
        cut = limit

    return text[:cut].rstrip() + " […]"


def title_from_query(query: str, limit: int = 60) -> str:
    """Human readable title for a search result derived from the question."""
    text = normalize_query(query) or (query or "").strip()

    return (text[:1].upper() + text[1:])[:limit] if text else "Search result"


def relevant_to(text: str, query: str, *, threshold: float = 0.2) -> bool:
    """
    Does this passage actually talk about what was asked?

    Used on the *write* path only. A search result may legitimately avoid the
    question's wording, so retrieval never filters on it - but before Nexus
    files something as a durable fact about a topic, it has to demonstrably be
    about that topic, or a background refresh could store a clock reading as
    the answer to a political question.
    """
    wanted = {word for word in tokens(query) if len(word) > 2}

    if len(wanted) < 2:
        return True

    haystack = {word for word in tokens(text) if len(word) > 2}

    if not haystack:
        return False

    return len(wanted & haystack) / len(wanted) >= threshold
