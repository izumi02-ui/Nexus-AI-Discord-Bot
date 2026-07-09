"""
Project Nexus

Search Cache
"""

from time import time

from utils.logger import logger


class SearchCache:

    DEFAULT_TTL = 300

    def __init__(self):

        self.cache = {}

        self.hits = 0

        self.misses = 0

    # ==========================================
    # Get
    # ==========================================

    def get(
        self,
        key: str,
    ):

        item = self.cache.get(key)

        if item is None:

            self.misses += 1

            return None

        expires, value = item

        if time() >= expires:

            del self.cache[key]

            self.misses += 1

            return None

        self.hits += 1

        return value

    # ==========================================
    # Set
    # ==========================================

    def set(
        self,
        key: str,
        value,
        ttl: int | None = None,
    ):

        if ttl is None:

            ttl = self.DEFAULT_TTL

        self.cache[key] = (

            time() + ttl,

            value,

        )

    # ==========================================
    # Remove
    # ==========================================

    def remove(
        self,
        key: str,
    ):

        self.cache.pop(
            key,
            None
        )

    # ==========================================
    # Clear
    # ==========================================

    def clear(self):

        self.cache.clear()

        logger.info(
            "Search cache cleared."
        )

    # ==========================================
    # Cleanup
    # ==========================================

    def cleanup(self):

        now = time()

        expired = [

            key

            for key, (expires, _)

            in self.cache.items()

            if expires <= now

        ]

        for key in expired:

            del self.cache[key]

        if expired:

            logger.info(
                f"Removed {len(expired)} expired cache entries."
            )

    # ==========================================
    # Stats
    # ==========================================

    @property
    def stats(self):

        return {

            "entries": len(self.cache),

            "hits": self.hits,

            "misses": self.misses,

        }


cache = SearchCache()
