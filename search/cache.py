"""
Project Nexus

Search Cache

Answers to "what is X" stay correct for a while; answers to "what is X right
now" do not. This cache therefore takes the query's freshness budget into
account when deciding how long to keep something, supports stale-while-
revalidate (serve the old result instantly, refresh in the background) and is
bounded so a long-lived bot cannot leak memory.
"""

import threading
import time
from collections import OrderedDict

from search.query import cache_key
from utils.logger import logger


class SearchCache:

    DEFAULT_TTL = 300

    MIN_TTL = 30

    MAX_ENTRIES = 512

    def __init__(self):

        self.cache = OrderedDict()

        self.hits = 0

        self.misses = 0

        self.stale_served = 0

        self.evictions = 0

        self._lock = threading.RLock()

        self._refreshing = set()

        #: key -> normalised topic, so a correction can invalidate by subject
        #: instead of by exact query string.
        self._topics: dict[str, str] = {}

    # ==========================================
    # Keys
    # ==========================================

    @staticmethod
    def key(query: str, tools=None) -> str:
        return cache_key(query, tools)

    # ==========================================
    # Get
    # ==========================================

    def get(
        self,
        key: str,
        *,
        max_age: float | None = None,
    ):
        """
        Return the cached value, or None.

        ``max_age`` overrides the entry's own TTL: pass the freshness budget of
        the current question so a 20-minute-old weather answer is not reused for
        a "right now" query.
        """
        key = self._normalize(key)

        with self._lock:
            item = self.cache.get(key)

            if item is None:
                self.misses += 1

                return None

            expires, stored_at, value = item

            age = time.time() - stored_at

            allowed = expires - stored_at

            if max_age is not None:
                allowed = min(allowed, max_age)

            if age > allowed:
                # Keep it briefly so it can still be served as stale fallback.
                if age > allowed * 4:
                    del self.cache[key]

                self.misses += 1

                return None

            self.hits += 1

            self.cache.move_to_end(key)

            return value

    def get_with_staleness(self, key: str, *, max_age: float | None = None):
        """
        -> (value, fresh) where value may be an expired entry.

        Used for stale-while-revalidate: answer quickly with yesterday's
        headline rather than not answering, but flag it as needing a refresh.
        """
        key = self._normalize(key)

        with self._lock:
            item = self.cache.get(key)

            if item is None:
                self.misses += 1

                return None, False

            expires, stored_at, value = item

            age = time.time() - stored_at

            allowed = expires - stored_at

            if max_age is not None:
                allowed = min(allowed, max_age)

            if age > allowed * 4:
                del self.cache[key]

                self.misses += 1

                return None, False

            if age > allowed:
                self.stale_served += 1

                return value, False

            self.hits += 1

            return value, True

    # ==========================================
    # Set
    # ==========================================

    def set(
        self,
        key: str,
        value,
        ttl: int | None = None,
        *,
        max_ttl: float | None = None,
        topic: str | None = None,
    ):
        key = self._normalize(key)

        if ttl is None:
            ttl = self.DEFAULT_TTL

        ttl = max(self.MIN_TTL, int(ttl))

        if max_ttl:
            ttl = max(self.MIN_TTL, min(ttl, int(max_ttl)))

        now = time.time()

        with self._lock:
            self.cache[key] = (now + ttl, now, value)

            if topic:
                from search.query import normalize_query

                self._topics[key] = normalize_query(topic) or topic.lower()

            self.cache.move_to_end(key)

            while len(self.cache) > self.MAX_ENTRIES:
                dropped, _ = self.cache.popitem(last=False)

                self._topics.pop(dropped, None)

                self.evictions += 1

    # ==========================================
    # In-flight bookkeeping (dedupe concurrent identical searches)
    # ==========================================

    def begin_refresh(self, key: str) -> bool:
        """True when this caller should do the work; False if one is running."""
        key = self._normalize(key)

        with self._lock:
            if key in self._refreshing:
                return False

            self._refreshing.add(key)

            return True

    def end_refresh(self, key: str):
        with self._lock:
            self._refreshing.discard(self._normalize(key))

    # ==========================================
    # Remove
    # ==========================================

    def remove(
        self,
        key: str,
    ):
        with self._lock:
            normalized = self._normalize(key)

            self.cache.pop(normalized, None)

            self._topics.pop(normalized, None)

    def invalidate_topic(self, topic: str) -> int:
        """
        Drop every entry whose cached value mentions a topic.

        Used when the knowledge updater re-verifies something: stale answers
        must not survive a correction.
        """
        from search.query import normalize_query, topic_of

        needle = (topic or "").lower().strip()

        if not needle:
            return 0

        # Callers pass either a raw query ("weather in delhi") or the stored
        # topic slug ("weather delhi"); both must find the same entries.
        needle_topic = " ".join(topic_of(needle).split())

        removed = 0

        with self._lock:
            for key in list(self.cache):
                _, _, value = self.cache[key]

                text = " ".join(
                    str(getattr(result, "title", "")) + " " + str(getattr(result, "content", ""))[:400]
                    for result in (value or [])
                ).lower()

                stored = self._topics.get(key, "")

                topic_hit = bool(
                    needle_topic
                    and stored
                    and (
                        stored == needle_topic
                        or stored in needle_topic
                        or needle_topic in stored
                    )
                )

                if needle in text or topic_hit:
                    del self.cache[key]

                    removed += 1

        return removed

    # ==========================================
    # Clear
    # ==========================================

    def clear(self):
        with self._lock:
            self.cache.clear()

            self._topics.clear()

        logger.info(
            "Search cache cleared."
        )

    # ==========================================
    # Cleanup
    # ==========================================

    def cleanup(self):

        now = time.time()

        with self._lock:
            expired = [
                key
                for key, (expires, _, _)
                in self.cache.items()
                if expires <= now
            ]

            for key in expired:
                del self.cache[key]

                self._topics.pop(key, None)

        if expired:
            logger.info(
                f"Removed {len(expired)} expired cache entries."
            )

        return len(expired)

    # ==========================================
    # Stats
    # ==========================================

    @property
    def stats(self):
        with self._lock:
            total = self.hits + self.misses

            return {
                "entries": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "stale_served": self.stale_served,
                "evictions": self.evictions,
                "hit_rate": round(self.hits / total, 3) if total else 0.0,
            }

    @staticmethod
    def _normalize(key: str) -> str:
        if len(key) in {24, 40}:
            return key

        return cache_key(key)


cache = SearchCache()
