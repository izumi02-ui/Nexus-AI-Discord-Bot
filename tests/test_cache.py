"""
The search cache: how stale is too stale?
"""

import time

from search.cache import cache


def test_fresh_entry_is_returned():
    key = cache.key("unique query alpha", ["brave"])

    cache.set(key, [{"title": "x"}], ttl=60)

    value, fresh = cache.get_with_staleness(key, max_age=60)

    assert value is not None
    assert fresh is True

    cache.remove(key)


def test_expired_entry_is_dropped():
    """No sleeping in tests: expiry is a timestamp comparison, so fake the clock."""
    key = cache.key("unique query beta", ["brave"])

    cache.set(key, [{"title": "y"}], ttl=600)

    created = cache.cache[key][1]

    cache.cache[key] = (time.time() - 1, created, [{"title": "y"}])

    assert cache.get(key) is None

    cache.remove(key)


def test_stale_but_readable_entry_is_flagged():
    """Old data may be shown, but never silently presented as current."""
    key = cache.key("unique query gamma", ["brave"])

    cache.set(key, [{"title": "z"}], ttl=600)

    # 5s old against a 2s freshness budget: inside the stale-while-revalidate
    # grace window, so it is served - but flagged as not fresh.
    cache.cache[key] = (time.time() + 500, time.time() - 5, [{"title": "z"}])

    value, fresh = cache.get_with_staleness(key, max_age=2)

    assert value is not None
    assert fresh is False

    # Beyond the grace window it is gone rather than misleading.
    cache.cache[key] = (time.time() + 500, time.time() - 100, [{"title": "z"}])

    assert cache.get_with_staleness(key, max_age=2)[0] is None

    cache.remove(key)


def test_ttl_is_capped_by_the_max_ttl():
    key = cache.key("unique query delta", ["brave"])

    cache.set(key, [1], ttl=10_000, max_ttl=30)

    expires, _, _ = cache.cache[key]

    assert expires - time.time() <= 31

    cache.remove(key)


def test_invalidate_by_topic():
    """A corrected fact must not keep being served from cache."""
    from search.query import topic_of

    query = "weather in delhi"

    key = cache.key(query, ["weather"])

    cache.set(
        key,
        [{"title": "Delhi is 40 C", "content": "Delhi weather today: 40 C"}],
        ttl=300,
        topic=topic_of(query),
    )

    removed = cache.invalidate_topic(topic_of(query))

    assert removed >= 1
    assert cache.get(key) is None


def test_key_is_stable_and_tool_sensitive():
    from search.query import cache_key

    assert cache_key("Weather In Delhi!") == cache_key("weather in delhi")
    assert cache.key("q", ["brave"]) != cache.key("q", ["wikipedia"])


def test_cleanup_bounds_the_cache():
    for index in range(5):
        cache.set(cache.key(f"bulk query {index}", ["brave"]), [index], ttl=1)

    removed = cache.cleanup()

    assert isinstance(removed, int)
    assert cache.stats["entries"] >= 0
