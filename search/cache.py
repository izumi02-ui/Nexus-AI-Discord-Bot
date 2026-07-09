"""
Project Nexus

Search Cache
"""

from time import time


class SearchCache:

    def __init__(self):

        self.cache = {}

    def get(
        self,
        key: str,
    ):

        item = self.cache.get(key)

        if item is None:

            return None

        expires, value = item

        if time() > expires:

            del self.cache[key]

            return None

        return value

    def set(
        self,
        key: str,
        value,
        ttl: int = 300,
    ):

        self.cache[key] = (
            time() + ttl,
            value
        )


cache = SearchCache()
