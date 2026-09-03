"""
Project Nexus

Search Aggregator

Runs the available evidence tools concurrently, merges, ranks and cross-checks
what comes back, and hands the result to the rest of the bot as a SearchReport.

Design rules that matter for accuracy:

  * partial results beat no results - a slow tool is cut off at the deadline
    and the rest still answers;
  * nothing is invented - a tool with no data contributes nothing;
  * freshness is respected - cache entries are only reused while the question
    they answer is still considered live;
  * the knowledge base is consulted first, so re-asking the same thing an hour
    later is free *and* still verified.
"""

import asyncio
import time
from typing import List

from search.cache import cache
from search.freshness import budget_for, classify
from search.query import topic_of
from search.ranking import ranking
from search.report import SearchReport
from search.search_result import SearchResult
from tools.manager import tool_manager
from utils.logger import logger
from utils.settings import settings


class SearchAggregator:

    def __init__(self):

        logger.info(
            "Search Aggregator Ready."
        )

        self.inflight: dict[str, asyncio.Task] = {}

    # ==========================================
    # Main entry point
    # ==========================================

    async def search(
        self,
        query: str,
        tools: List[str] | None = None,
        *,
        budget: int | None = None,
        timeout: float | None = None,
        use_cache: bool = True,
        force: bool = False,
        user_id: int | None = None,
    ) -> SearchReport:
        started = time.monotonic()

        query = (query or "").strip()

        if not query:
            return SearchReport(
                query=query,
                error="empty query",
                freshness="n/a",
            )

        freshness_class = classify(query)
        budget = budget or budget_for(query)

        key = cache.key(query, tools)

        # ==========================
        # Cache
        # ==========================
        if use_cache and not force:
            cached, fresh = cache.get_with_staleness(key, max_age=budget)

            if cached is not None:
                report = self._from_cached(query, cached, budget, freshness_class, started)

                report.stale = not fresh
                report.from_cache = True

                if not fresh:
                    logger.info(
                        "Serving stale cache for %r and refreshing in background.",
                        query,
                    )
                    self._refresh_in_background(query, tools, key)

                return report

        # ==========================
        # Tools
        # ==========================
        requested = list(tools) if tools else None

        selected = tool_manager.select(requested)

        skipped = [
            name
            for name in (requested or [])
            if tool_manager.get(name) is None or not tool_manager.get(name).usable
        ]

        if not selected:
            logger.warning(
                "No usable search tools for %r - answering without evidence.",
                query,
            )

            return SearchReport(
                query=query,
                tools_skipped=skipped,
                budget=budget,
                freshness=freshness_class,
                elapsed=time.monotonic() - started,
                error="no search tools available",
            )

        timeout = timeout or getattr(settings, "search_timeout", 18.0)

        logger.info(
            "Searching '%s' with %s (budget %ss, timeout %ss)",
            query,
            ", ".join(tool.name for tool in selected),
            budget,
            timeout,
        )

        raw_results, failures = await self._gather(selected, query, timeout)

        # ==========================
        # Rank + cross-check
        # ==========================
        ranked = ranking.rank(
            raw_results,
            query,
            budget=budget,
            max_results=getattr(settings, "max_sources", 6),
        )

        cross = ranking.cross_check(ranked)

        # ==========================
        # Cache
        # ==========================
        if use_cache and ranked:
            cache.set(
                key,
                ranked,
                ttl=self._ttl_for(selected, budget),
                max_ttl=budget,
                topic=topic_of(query),
            )

        for tool in selected:
            tool_manager.record_result(
                tool.name,
                sum(1 for result in ranked if result.tool == tool.name),
            )

        report = SearchReport(
            query=query,
            results=ranked,
            tools_used=[tool.name for tool in selected],
            tools_skipped=skipped,
            tools_failed=failures,
            cross=cross,
            budget=budget,
            freshness=freshness_class,
            elapsed=time.monotonic() - started,
        )

        logger.info(
            "Evidence for %r: %s result(s), %s domain(s), mean %.2f, %s",
            query,
            len(ranked),
            cross.get("sources", 0),
            cross.get("confidence", 0.0),
            f"{report.elapsed:.1f}s",
        )

        return report

    # ==========================================
    # Convenience wrappers
    # ==========================================

    async def quick(
        self,
        query: str,
        tools: List[str] | None = None,
    ) -> List[SearchResult]:
        """Plain list of results, for API routes and tests."""
        report = await self.search(query, tools)

        return report.results

    async def lookup(
        self,
        query: str,
        *,
        tool: str | None = None,
    ) -> SearchResult | None:
        """Best single answer for a question, or None."""
        report = await self.search(query, [tool] if tool else None)

        return report.best

    async def refresh(
        self,
        query: str,
        tools: List[str] | None = None,
    ) -> SearchReport:
        """Bypass the cache entirely - used by the self-updater."""
        return await self.search(query, tools, use_cache=False, force=True)

    def stats(self) -> dict:
        return {
            "cache": cache.stats,
            "inflight": len(self.inflight),
        }

    # ==========================================
    # Internals
    # ==========================================

    async def _gather(self, tools, query: str, timeout: float):
        """
        Run tools concurrently with a single deadline.

        Tools that finish in time are used; the rest are cancelled. A dead API
        therefore costs the deadline, not the whole answer.
        """
        tasks = {
            asyncio.create_task(
                asyncio.wait_for(tool.execute(query), timeout=timeout),
                name=f"tool:{tool.name}",
            ): tool
            for tool in tools
        }

        results: List[SearchResult] = []
        failures: dict[str, str] = {}

        if not tasks:
            return results, failures

        done, pending = await asyncio.wait(
            set(tasks),
            timeout=timeout + 1.0,
        )

        for task in pending:
            tool = tasks[task]

            task.cancel()

            failures[tool.name] = "timed out"

            logger.warning("Tool %s timed out after %ss", tool.name, timeout)

        for task in done:
            tool = tasks[task]

            try:
                outcome = task.result()
            except asyncio.CancelledError:  # pragma: no cover
                continue
            except Exception as error:  # noqa: BLE001 - one tool must not sink the rest
                failures[tool.name] = str(error)[:200]

                logger.warning(
                    "%s failed: %s",
                    tool.name,
                    error,
                )
                continue

            if isinstance(outcome, dict) and outcome.get("success") is False:
                failures[tool.name] = str(outcome.get("error"))[:200]
                continue

            if isinstance(outcome, dict):
                outcome = [outcome.get("result")]

            if isinstance(outcome, SearchResult):
                outcome = [outcome]

            if not outcome:
                continue

            for result in outcome:
                if not isinstance(result, SearchResult):
                    continue

                result.stamp(tool=tool.name)

                ttl = getattr(tool, "ttl", None)

                if ttl:
                    result.metadata.setdefault("tool_ttl", ttl)

                results.append(result)

        if failures:
            logger.info(
                "Tool failures: %s",
                "; ".join(f"{name}: {why}" for name, why in failures.items()),
            )

        return results, failures

    def _ttl_for(self, tools, budget: int) -> int:
        """Shortest suggested TTL among the tools that answered, capped by budget."""
        ttls = [
            tool.ttl
            for tool in tools
            if getattr(tool, "ttl", None)
        ]

        ttl = min(ttls) if ttls else cache.DEFAULT_TTL

        if getattr(settings, "cache_freshness_aware", True):
            ttl = min(ttl, max(cache.MIN_TTL, budget))

        return int(ttl)

    def _from_cached(self, query, results, budget, freshness_class, started) -> SearchReport:
        ranked = ranking.rank(results, query, budget=budget)

        return SearchReport(
            query=query,
            results=ranked,
            cross=ranking.cross_check(ranked),
            budget=budget,
            freshness=freshness_class,
            elapsed=time.monotonic() - started,
            tools_used=["cache"],
        )

    def _refresh_in_background(self, query: str, tools, key: str):
        """
        Answer now, fix the cache soon.

        A background revalidation is the difference between "always slightly
        out of date" and "never blocks the user while getting current".
        """
        if not cache.begin_refresh(key):
            return

        async def _run():
            try:
                await self.search(
                    query,
                    tools,
                    use_cache=True,
                    force=True,
                )
            except Exception as error:  # noqa: BLE001 - best effort
                logger.debug("Background refresh failed: %s", error)
            finally:
                cache.end_refresh(key)

        try:
            task = asyncio.get_running_loop().create_task(_run())

            self.inflight[key] = task

            task.add_done_callback(lambda _done: self.inflight.pop(key, None))
        except RuntimeError:  # no loop (unit tests)
            cache.end_refresh(key)


aggregator = SearchAggregator()
