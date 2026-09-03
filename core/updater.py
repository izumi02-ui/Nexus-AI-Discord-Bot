"""
Project Nexus

Knowledge Updater

The background service that keeps Nexus correct over time instead of only at
the moment it was started.

Each cycle does five things, none of them optional in spirit:

    1. refresh runtime facts      - clock, version, active provider/model,
                                    how many tools and sources are alive
    2. probe the tools            - a real query against each evidence tool,
                                    so a dead integration is discovered before
                                    a user runs into it
    3. re-verify stored knowledge - every knowledge row past its shelf life is
                                    looked up again; changed values are
                                    updated with history, contradictions become
                                    "disputed" rather than silently trusted
    4. keep hot topics warm       - topics the community keeps asking about are
                                    refreshed ahead of the next question
    5. maintain caches            - expired search cache entries and weak
                                    knowledge rows are dropped

It is a single asyncio task on the bot's loop: no cron, no extra process, no
external queue - which is what makes it survive a Render free-tier sleep.
"""

import asyncio
import re
import time
from datetime import timedelta

from database import knowledge
from database.database import database
from search.aggregator import aggregator
from search.query import relevant_to
from search.cache import cache
from utils.logger import logger
from utils.settings import settings
from utils.time_utils import (
    INDIA_TIMEZONE,
    humanize_age,
    iso,
    now_utc,
)

#: A probe must be cheap and unambiguous: the tool answers a question whose
#: correct response is machine-checkable.
#: Tools the background jobs are allowed to use. Deliberately narrow: a
#: scheduled refresh should corroborate, not wake up fifteen APIs.
REFRESH_TOOLS = ("brave", "google", "web_search", "wikipedia", "news")


PROBES = {
    "weather": "weather in London",
    "currency": "100 usd to inr",
    "time": "what time is it in Tokyo",
    "wikipedia": "Wikipedia",
    "news": "technology",
    "github": "izumi02-ui/Nexus-AI-Discord-Bot",
    "arxiv": "attention is all you need",
    "stackoverflow": "python dict get default",
    "duckduckgo": "Tokyo",
    "calculator": "17*23",
    "web_scraper": "https://example.com",
    "translator": "translate hello to French",
    "maps": "where is the Eiffel Tower",
    "reddit": "python programming",
    "steam": "civilization vi",
    "brave": "current prime minister of Japan",
    "google": "current prime minister of Japan",
    "web_search": "current prime minister of Japan",
}

RUNTIME_TOPICS = {
    "clock": "It is {utc} UTC ({india} IST).",
    "build": "Project Nexus {version} is running on provider {provider} with model {model}.",
    "capacity": (
        "Nexus currently has {tools} evidence tool(s) answering, {sources} "
        "verified knowledge entries and a cache hit rate of {hit_rate}."
    ),
}


class KnowledgeUpdater:

    def __init__(self):

        self.task = None

        self.stop_event = asyncio.Event()

        self.running = False

        self.state = {
            "cycles": 0,
            "last_cycle_at": None,
            "last_cycle_seconds": None,
            "last_error": None,
            "last_result": {},
            "started_at": None,
            "next_refresh": None,
        }

        self._lock = asyncio.Lock()

        self._last_probe = 0.0

    # ==========================================
    # Lifecycle
    # ==========================================

    def start(self):
        """Start the periodic loop. Safe to call more than once."""
        if not getattr(settings, "self_update_enabled", True):
            logger.info(
                "Knowledge updater disabled (SELF_UPDATE_ENABLED=false)."
            )

            return None

        if self.task and not self.task.done():
            return self.task

        self.stop_event.clear()

        self.state["started_at"] = iso(now_utc())

        self.task = asyncio.create_task(
            self._loop(), name="nexus:knowledge-updater"
        )

        logger.info(
            "Knowledge updater started (every %s).",
            humanize_age(
                now_utc() - timedelta(seconds=settings.self_update_interval),
                reference=now_utc(),
            ).replace("ago", "") + " intervals",
        )

        return self.task

    async def stop(self):
        self.stop_event.set()

        if self.task:
            self.task.cancel()

            try:
                await self.task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

        logger.info("Knowledge updater stopped.")

    async def _loop(self):
        interval = max(60, int(getattr(settings, "self_update_interval", 3600)))

        # Give the bot a moment to finish logging in and answering anything
        # already queued before background work starts competing for the API.
        while not self.stop_event.is_set():
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=12)
            except asyncio.TimeoutError:
                pass

            await self.run_once(reason="scheduled")

            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=interval)

                break
            except asyncio.TimeoutError:
                continue

        logger.info("Knowledge updater loop exited.")

    # ==========================================
    # One cycle
    # ==========================================

    async def run_once(self, *, reason: str = "manual", probe: bool | None = None) -> dict:
        """
        Run one full maintenance cycle and report what happened.

        Re-entrant safe: a /refresh while a scheduled cycle is running simply
        waits, so two writers never fight over the same rows.
        """
        async with self._lock:
            started = time.monotonic()

            self.running = True

            result = {
                "reason": reason,
                "at": iso(now_utc()),
                "runtime": {},
                "tools": {},
                "reverified": {},
                "watched": {},
                "maintenance": {},
                "error": None,
            }

            try:
                result["runtime"] = await self.refresh_runtime_facts()

                should_probe = (
                    probe
                    if probe is not None
                    else self._due(self._last_probe, getattr(settings, "tool_probe_interval", 1800))
                )

                if should_probe:
                    result["tools"] = await self.probe_tools()

                    self._last_probe = time.time()

                result["reverified"] = await self.reverify_knowledge()

                result["watched"] = await self.refresh_watchlist()

                result["maintenance"] = self.maintain()

                if getattr(settings, "model_auto_refresh", True) and reason == "scheduled":
                    from ai import model_catalog

                    try:
                        result["models"] = await model_catalog.refresh()
                    except Exception as error:  # noqa: BLE001
                        result["models"] = {"error": str(error)[:200]}

            except Exception as error:  # noqa: BLE001 - the loop must survive
                result["error"] = str(error)[:400]

                self.state["last_error"] = result["error"]

                logger.exception("Knowledge updater cycle failed.")

            elapsed = time.monotonic() - started

            result["seconds"] = round(elapsed, 2)

            self.state.update(
                cycles=self.state["cycles"] + 1,
                last_cycle_at=result["at"],
                last_cycle_seconds=round(elapsed, 2),
                last_result=result,
                next_refresh=iso(
                    now_utc() + timedelta(seconds=settings.self_update_interval)
                ),
            )

            database.set_state("updater_last_run", result["at"])
            database.set_state(
                "updater_last_summary",
                f"{result['reverified'].get('checked', 0)} rechecked, "
                f"{result['reverified'].get('updated', 0)} updated",
            )

            logger.info(
                "Updater cycle finished in %.1fs (%s).",
                elapsed,
                reason,
            )

            self.running = False

            return result

    # ==========================================
    # 1. Runtime facts
    # ==========================================

    async def refresh_runtime_facts(self) -> dict:
        """
        Store the facts Nexus needs to describe itself accurately.

        Without this, "what are you running on?" and "what time is it?" get
        answered from whatever the model believed at training time - which is
        how a bot ends up stating last year's version number as current.
        """
        from ai.engine import engine
        from ai.provider_manager import provider_manager

        from tools.manager import tool_manager

        from config import VERSION

        facts = {}

        clock = RUNTIME_TOPICS["clock"].format(
            utc=now_utc().strftime("%A, %d %B %Y, %H:%M"),
            india=now_utc().astimezone(INDIA_TIMEZONE).strftime(
                "%A, %d %B %Y, %I:%M %p"
            ),
        )

        facts["clock"] = knowledge.remember(
            clock,
            topic="nexus clock",
            claim="current time",
            source="system clock",
            tool="runtime",
            confidence=1.0,
            ttl_seconds=300,
            reason="runtime refresh",
        )

        build = RUNTIME_TOPICS["build"].format(
            version=VERSION,
            provider=provider_manager.name,
            model=provider_manager.model,
        )

        facts["build"] = knowledge.remember(
            build,
            topic="nexus build",
            claim="running configuration",
            source="Nexus runtime",
            tool="runtime",
            confidence=1.0,
            ttl_seconds=900,
            reason="runtime refresh",
        )

        usable = tool_manager.usable_tools()

        capacity = RUNTIME_TOPICS["capacity"].format(
            tools=len(usable),
            sources=knowledge.stats().get("active") or 0,
            hit_rate=cache.stats["hit_rate"],
        )

        facts["capacity"] = knowledge.remember(
            capacity,
            topic="nexus capacity",
            claim="evidence coverage",
            source="Nexus runtime",
            tool="runtime",
            confidence=1.0,
            ttl_seconds=1800,
            reason="runtime refresh",
        )

        database.set_state("runtime_clock", clock)
        database.set_state("runtime_build", build)

        return {
            "written": len([value for value in facts.values() if value]),
            "tools": len(usable),
            "provider": provider_manager.name,
            "model": provider_manager.model,
            "requests": engine.stats["requests"],
        }

    # ==========================================
    # 2. Tool probes
    # ==========================================

    async def probe_tools(self, *, limit: int = 12) -> dict:
        """
        Ask every configured tool one known-answer question.

        The point is not to grade the answer, only to learn whether the tool
        still responds with anything usable at all.
        """
        from tools.manager import tool_manager

        report = {"checked": 0, "healthy": 0, "broken": [], "skipped": []}

        tools = [tool for tool in tool_manager.tools.values() if tool.implemented]

        tools = tools[:limit]

        for tool in tools:
            if not tool.available:
                report["skipped"].append(tool.name)

                self._save_health(tool.name, None, note="not configured")

                continue

            query = PROBES.get(tool.name, "Nexus")

            try:
                outcome = await asyncio.wait_for(
                    tool.execute(query), timeout=min(12.0, settings.search_timeout)
                )

                count = len(outcome) if isinstance(outcome, list) else 1

                if isinstance(outcome, dict) and outcome.get("success") is False:
                    raise RuntimeError(str(outcome.get("error"))[:120])

                usable = [
                    result
                    for result in (outcome if isinstance(outcome, list) else [])
                    if getattr(result, "success", True)
                    and len(getattr(result, "content", "") or "") > 40
                ]

                if isinstance(outcome, list) and not usable:
                    raise RuntimeError("no usable content returned")

                report["checked"] += 1
                report["healthy"] += 1

                self._save_health(tool.name, count)

            except Exception as error:  # noqa: BLE001 - probe failures are data
                report["checked"] += 1

                report["broken"].append(f"{tool.name}: {str(error)[:120]}")

                self._save_health(tool.name, 0, error=str(error))

                tool.record_failure(error)

        return report

    def _save_health(self, name: str, samples: int | None, *, error: str | None = None, note: str | None = None):
        now = iso(now_utc())

        database.execute(
            """
            INSERT INTO tool_health(tool, available, last_sample, last_ok, last_error, checked_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tool) DO UPDATE SET
                available = excluded.available,
                last_sample = COALESCE(excluded.last_sample, tool_health.last_sample),
                last_ok = CASE WHEN excluded.last_sample > 0 THEN excluded.last_ok ELSE tool_health.last_ok END,
                last_error = COALESCE(excluded.last_error, tool_health.last_error),
                checked_at = excluded.checked_at,
                note = COALESCE(excluded.note, tool_health.note)
            """,
            (
                name,
                1 if (samples or 0) > 0 else 0,
                samples,
                now if (samples or 0) > 0 else None,
                error,
                now,
                note,
            ),
        )

    def health_rows(self) -> list[dict]:
        rows = database.fetchall(
            "SELECT * FROM tool_health ORDER BY checked_at DESC LIMIT 40"
        )

        return [dict(row) for row in rows]

    # ==========================================
    # 3. Re-verify stored knowledge
    # ==========================================

    async def reverify_knowledge(self, *, limit: int = 6) -> dict:
        """
        Re-run the search behind every expired claim.

        Three outcomes per row: confirmed (confidence up, clock reset),
        changed (new value stored, old value kept in history) or disputed
        (the tools contradicted the note, so it stops being quoted as fact).
        """
        rows = knowledge.stale_rows(limit=limit)

        summary = {
            "checked": len(rows),
            "confirmed": 0,
            "updated": 0,
            "disputed": 0,
            "unreachable": 0,
        }

        for row in rows:
            query = f"{row['topic']} {row['claim'] or ''}".strip()

            try:
                report = await aggregator.refresh(query, self._tools_for(row.get("tool")))
            except Exception as error:  # noqa: BLE001 - retry next cycle
                summary["unreachable"] += 1

                logger.debug("Re-verification failed for %s: %s", row["topic"], error)

                continue

            if report.is_empty:
                summary["unreachable"] += 1

                knowledge.mark_stale(row["id"], "re-check returned nothing")

                continue

            best = report.best

            new_value = " ".join((best.content or "").split())

            if not relevant_to(new_value, query):
                # The refresh found something, but not about this topic.
                summary["irrelevant"] = summary.get("irrelevant", 0) + 1

                knowledge.mark_stale(
                    row["id"],
                    "re-check could not confirm this topic",
                )

                continue

            if same_claim(row["value"], new_value):
                knowledge.remember(
                    row["value"],
                    topic=row["topic"],
                    claim=row["claim"] or "",
                    source=best.source or row["source"],
                    url=best.url or row["url"],
                    tool=best.tool or row["tool"],
                    confidence=min(0.95, float(row["confidence"] or 0.7) + 0.03),
                    ttl_seconds=row["ttl_seconds"] or settings.knowledge_ttl,
                    reason="re-verified",
                )

                summary["confirmed"] += 1

                continue

            knowledge.remember(
                new_value[:1200],
                topic=row["topic"],
                claim=row["claim"] or "",
                source=best.source,
                url=best.url,
                tool=best.tool,
                confidence=min(0.9, float(best.score_of() or 0.6)),
                ttl_seconds=row["ttl_seconds"] or settings.knowledge_ttl,
                reason="changed on re-verification",
            )

            summary["updated"] += 1

            cache.invalidate_topic(row["topic"])

            logger.info(
                "Knowledge self-corrected (%s): %r -> %r",
                row["topic"],
                (row["value"] or "")[:70],
                new_value[:70],
            )

        return summary

    # ==========================================
    # 4. Watchlist
    # ==========================================

    async def refresh_watchlist(self, *, limit: int = 4) -> dict:
        """
        Pre-fetch the topics the server keeps asking about.

        A question that arrives while its answer is already verified is
        answered instantly *and* correctly, which is the only way a small bot
        beats a large one on the same free model.
        """
        topics = knowledge.watchlist(limit=limit)

        summary = {"queued": len(topics), "refreshed": 0, "empty": 0}

        for row in topics:
            query = row.get("sample") or row["topic"]

            try:
                report = await aggregator.refresh(query, self._tools_for())
            except Exception as error:  # noqa: BLE001
                summary["empty"] += 1

                logger.debug("Watchlist refresh failed for %s: %s", row["topic"], error)

                continue

            if report.is_empty:
                summary["empty"] += 1

                continue

            knowledge.remember(
                " ".join((report.best.content or "").split())[:1200],
                topic=row["topic"],
                claim=(report.best.title or "watchlist")[:180],
                source=report.best.source,
                url=report.best.url,
                tool=report.best.tool,
                confidence=min(0.88, float(report.best.score_of() or 0.6)),
                ttl_seconds=settings.knowledge_ttl,
                reason="watchlist refresh",
            )

            knowledge.mark_refreshed(row["topic"])

            summary["refreshed"] += 1

        return summary

    # ==========================================
    # 5. Maintenance
    # ==========================================

    def maintain(self) -> dict:
        removed = cache.cleanup()

        pruned = knowledge.prune(
            min_confidence=settings.knowledge_min_confidence,
            keep=settings.knowledge_max_entries,
        )

        return {"cache_entries_removed": removed, "knowledge_pruned": pruned}

    # ==========================================
    # Status
    # ==========================================

    def status(self) -> dict:
        return {
            **self.state,
            "running": self.running,
            "enabled": bool(getattr(settings, "self_update_enabled", True)),
            "interval_seconds": int(getattr(settings, "self_update_interval", 3600)),
            "knowledge": knowledge.stats(),
            "cache": cache.stats,
        }

    def _tools_for(self, preferred: str | None = None) -> list[str]:
        """Narrow tool list for background work, filtered to what is usable."""
        from tools.manager import tool_manager

        names = []

        if preferred and preferred in tool_manager.tools:
            names.append(preferred)

        for name in REFRESH_TOOLS:
            tool = tool_manager.get(name)

            if tool and tool.usable and name not in names:
                names.append(name)

        return names or [
            tool.name
            for tool in tool_manager.search_tools()[:2]
        ]

    def _due(self, last: float, interval: float) -> bool:
        if not last:
            return True

        return (time.time() - last) >= interval


def aggregator_tool_names() -> set[str]:
    from tools.manager import tool_manager

    return set(tool_manager.tools.keys())


#: The part of a sentence that actually carries the fact.
NUM_RE = re.compile(
    r"\d+(?:[.,]\d+)*\s?(?:%|percent|million|billion|trillion|thousand|km|kg|c)?"
)


def same_claim(first: str, second: str) -> bool:
    """
    Is the refreshed text the same claim, worded differently?

    Deliberately lenient: only a meaningful difference should rewrite history,
    otherwise a paraphrased headline looks like a correction every hour. Two
    tests are used because neither is sufficient alone - wording drifts, but
    the numbers in a fact do not.
    """
    from difflib import SequenceMatcher

    a = " ".join((first or "").lower().split())
    b = " ".join((second or "").lower().split())

    if not a or not b:
        return False

    if a == b:
        return True

    short, long = (a, b) if len(a) <= len(b) else (b, a)

    if len(short) >= 24 and short in long:
        return True

    numbers_a = set(NUM_RE.findall(a))

    numbers_b = set(NUM_RE.findall(b))

    similarity = SequenceMatcher(None, a[:900], b[:900]).ratio()

    if numbers_a and numbers_a == numbers_b:
        # Same figures, different sentence: a re-report, not a correction.
        return similarity >= 0.55

    if numbers_a and numbers_b and numbers_a != numbers_b:
        # Different figures: that is a change, however similar the sentences look.
        return False

    return similarity >= 0.86


updater = KnowledgeUpdater()
