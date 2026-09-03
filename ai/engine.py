"""
Project Nexus

Central AI orchestration layer.

One request, in order:

    route      what does this message need? (chat / evidence / calculator / local)
    recall     has Nexus already verified something that answers it?
    retrieve   ask the tools, rank and cross-check what they return
    compose    build the conversation: persona, memory, evidence
    answer     one provider call, with fallbacks
    verify     compare the draft with the evidence; re-ask if it cannot stand
    learn      store the exchange, the durable facts, and the verified answer

Only the "answer" step talks to a language model on purpose: everything before
it decides *what the model is allowed to know*, and everything after it decides
*what Nexus is allowed to claim*.
"""

import time
from collections import OrderedDict

from ai.conversation_manager import conversation_manager
from ai.memory_extractor import memory_extractor
from ai.provider_manager import provider_manager
from ai.request_router import request_router
from ai.verifier import verifier

from database import knowledge
from database.memory import add_message

from search.aggregator import aggregator
from search.query import relevant_to, topic_of

from utils.logger import logger
from utils.response_formatter import response_formatter
from utils.settings import settings

#: Sources a repair pass may use when the first pass came back empty.
REPAIR_TOOLS = (
    "brave",
    "google",
    "web_search",
    "wikipedia",
    "news",
    "duckduckgo",
)

MAX_EXCHANGE_CHARS = 6000

RECENT_REPORTS = 64


class AIEngine:

    def __init__(self):
        self.provider = provider_manager

        self.reports: OrderedDict[int, dict] = OrderedDict()

        self.stats = {
            "requests": 0,
            "searched": 0,
            "grounded": 0,
            "retried": 0,
            "refusals": 0,
            "knowledge_hits": 0,
            "cache_hits": 0,
            "total_seconds": 0.0,
        }

        logger.info("AI Engine initialized.")

    # ==========================================
    # Entry points
    # ==========================================

    async def ask(
        self,
        user_id: int,
        message: str,
        *,
        context_note: str | None = None,
        attachments: list[str] | None = None,
    ) -> str:
        """Answer a user. Returns text ready for Discord."""
        outcome = await self.respond(
            user_id=user_id,
            message=message,
            context_note=context_note,
            attachments=attachments,
        )

        return outcome["response"]

    async def respond(
        self,
        user_id: int,
        message: str,
        *,
        context_note: str | None = None,
        include_footer: bool = True,
        attachments: list[str] | None = None,
        has_attachment: bool | None = None,
    ) -> dict:
        """
        Answer a user and return the full outcome.

        The metadata is what makes /sources, the API and the tests able to see
        *why* an answer looks the way it does.
        """
        started = time.monotonic()

        message = (message or "").strip()

        self.stats["requests"] += 1

        logger.info("Processing request from %s", user_id)

        attachments = [url for url in (attachments or []) if url]

        if has_attachment is None:
            has_attachment = bool(attachments)

        if attachments:
            context_note = self._attachment_note(context_note, attachments)

        route = request_router.route(
            message,
            has_attachment=has_attachment,
        )

        # ==========================
        # Small talk
        # ==========================
        if route["type"] == "local":
            reply = request_router.local_response(message)

            return {
                "response": response_formatter.format(
                    reply, user_id=None if not include_footer else user_id
                ),
                "raw": reply,
                "type": "local",
                "route": route,
                "report": None,
                "verification": None,
                "elapsed": time.monotonic() - started,
            }

        # ==========================
        # What Nexus already knows
        # ==========================
        remembered = []

        if route["type"] != "search" or route["freshness"] not in {"instant", "short"}:
            remembered = knowledge.recall(
                message,
                limit=3,
                min_confidence=getattr(settings, "knowledge_min_confidence", 0.35) + 0.15,
            )

            if remembered:
                self.stats["knowledge_hits"] += 1

        # ==========================
        # Live evidence
        # ==========================
        report = None

        if route["type"] == "search":
            report = await self._gather(message, route, user_id)

            if report is not None:
                if report.from_cache:
                    self.stats["cache_hits"] += 1

                self._remember_report(user_id, message, report)

        # ==========================
        # Compose + answer
        # ==========================
        conversation = await conversation_manager.build(
            user_id=user_id,
            message=message,
            report=report,
            remembered=remembered,
            context_note=context_note,
        )

        response = await self.provider.ask(
            user_id=user_id,
            conversation=conversation,
        )

        verification = verifier.verify(
            query=message,
            answer=response,
            report=report,
            freshness=route["freshness"],
            knowledge_rows=remembered,
        )

        # ==========================
        # Re-ask once, with the evidence in front of it
        # ==========================
        if (
            verification.needs_retry
            and getattr(settings, "auto_retry_with_search", True)
        ):
            self.stats["retried"] += 1

            response, verification, report = await self._reask(
                user_id=user_id,
                message=message,
                route=route,
                report=report,
                remembered=remembered,
                failed_answer=verification.answer,
            )

        if verification.grounded:
            self.stats["grounded"] += 1

        if verification.refused:
            self.stats["refusals"] += 1

        # ==========================
        # Learn
        # ==========================
        self._persist(user_id, message, verification.answer, report, verification)

        # ==========================
        # Format
        # ==========================
        text = response_formatter.format(
            verification.answer,
            user_id=user_id if include_footer else None,
        )

        text = self._decorate(text, verification, report, include_footer)

        elapsed = time.monotonic() - started

        self.stats["total_seconds"] += elapsed

        self.reports[user_id] = {
            "query": message,
            "report": report,
            "verification": verification,
            "route": route,
            "at": time.time(),
        }

        while len(self.reports) > RECENT_REPORTS:
            self.reports.popitem(last=False)

        logger.info(
            "Answered %s in %.1fs (%s)",
            user_id,
            elapsed,
            verification.summary,
        )

        return {
            "response": text,
            "raw": verification.answer,
            "type": route["type"],
            "route": route,
            "report": report,
            "verification": verification,
            "elapsed": elapsed,
        }

    # ==========================================
    # Evidence
    # ==========================================

    def _attachment_note(self, context_note, attachments: list[str]) -> str:
        """
        Tell the model what was attached, and whether it can actually see it.

        Being explicit here matters for accuracy: a model that silently ignores
        an image will still describe its contents confidently if nothing says
        otherwise.
        """
        vision = provider_manager.provider_supporting("vision") is not None

        lines = [
            f"The user attached {len(attachments)} file(s): "
            + ", ".join(attachments[:3])
        ]

        if vision:
            lines.append(
                "You can view these files; use whatever is relevant to the question."
            )
        else:
            lines.append(
                "If the answer depends on what an image shows, say you cannot see "
                "it with this provider and ask the user to paste the text instead - "
                "never guess at the contents."
            )

        note = "\n".join(lines)

        return f"{context_note}\n\n{note}" if context_note else note

    async def _gather(self, message: str, route: dict, user_id: int):
        try:
            report = await aggregator.search(
                query=message,
                tools=route.get("tools") or None,
                budget=route.get("budget"),
                user_id=user_id,
            )
        except Exception as error:  # noqa: BLE001 - never fail the reply on search
            logger.warning("Search failed: %s", error)

            return None

        self.stats["searched"] += 1

        return report

    def _remember_report(self, user_id: int, message: str, report) -> None:
        """Distill verified evidence into the knowledge base (self-updating)."""
        if report is None or not report.results:
            return

        if not report.is_grounded(int(getattr(settings, "min_sources_for_grounding", 1))):
            return

        if not report.cross.get("corroborated") and len(report) < 2:
            return

        best = report.best

        if not relevant_to(best.content or "", message):
            return

        try:
            knowledge.remember(
                self._digest(best),
                topic=topic_of(message),
                claim=(best.title or "")[:180],
                source=best.source,
                url=best.url,
                tool=best.tool,
                confidence=min(0.9, float(best.score_of() or 0.7)),
                ttl_seconds=self._ttl(message, report),
                reason="answer grounded",
            )
        except Exception as error:  # noqa: BLE001
            logger.debug("Knowledge write skipped: %s", error)

    def _digest(self, result) -> str:
        from search.query import truncate_words

        return truncate_words(" ".join((result.content or "").split()), 700)

    def _ttl(self, message: str, report) -> int:
        from search.freshness import budget_for

        return max(300, min(int(report.budget or budget_for(message)), 7 * 24 * 3600))

    # ==========================================
    # Retry
    # ==========================================

    async def _reask(
        self,
        *,
        user_id,
        message,
        route,
        report,
        remembered,
        failed_answer,
    ):
        """
        One repair pass.

        If the first answer had no evidence at all, force a real search now -
        because a model that says "the price is $4" with nothing backing it is
        the failure mode this whole pipeline exists to prevent.

        The repair pass is bounded on purpose: general web sources plus
        whatever the router originally picked, minus the tools that already
        failed seconds ago. Waking up the entire toolchain for one retry would
        turn a wrong answer into a slow, expensive wrong answer.
        """
        if report is None or report.is_empty:
            try:
                from tools.manager import tool_manager

                broken = set((report.tools_failed if report else {}) or {})

                wanted = list(
                    dict.fromkeys(
                        list(REPAIR_TOOLS) + list(route.get("tools") or [])
                    )
                )

                tools = [
                    name
                    for name in wanted
                    if name not in broken
                    and tool_manager.get(name) is not None
                    and tool_manager.get(name).usable
                ][:5]

                report = await aggregator.search(
                    message,
                    tools or None,
                    budget=route.get("budget"),
                    use_cache=False,
                    force=True,
                )
            except Exception as error:  # noqa: BLE001
                logger.warning("Repair search failed: %s", error)

        conversation = await conversation_manager.build(
            user_id=user_id,
            message=message,
            report=report,
            remembered=remembered,
            retry_instruction=verifier.reask_instruction(
                verifier.verify(
                    query=message,
                    answer=failed_answer,
                    report=report,
                    freshness=route["freshness"],
                )
            ),
        )

        try:
            response = await provider_manager.ask(
                user_id=user_id,
                conversation=conversation,
            )
        except Exception as error:  # noqa: BLE001 - keep the first answer
            logger.warning("Repair answer failed, keeping original: %s", error)

            verification = verifier.verify(
                query=message,
                answer=failed_answer,
                report=report,
                freshness=route["freshness"],
                knowledge_rows=remembered,
            )

            verification.needs_retry = False

            return failed_answer, verification, report

        verification = verifier.verify(
            query=message,
            answer=response,
            report=report,
            freshness=route["freshness"],
            knowledge_rows=remembered,
            # No second retry: a bounded loop, or this becomes a cost sink.
            # With retry spent, the verifier's remaining lever is refusal.
            allow_retry=False,
        )

        verification.needs_retry = False

        self._remember_report(user_id, message, report)

        return verification.answer, verification, report

    # ==========================================
    # Persistence
    # ==========================================

    def _persist(self, user_id, message, answer, report, verification) -> None:
        try:
            add_message(
                user_id=user_id,
                role="user",
                content=message[:MAX_EXCHANGE_CHARS],
            )

            add_message(
                user_id=user_id,
                role="assistant",
                content=(answer or "")[:MAX_EXCHANGE_CHARS],
            )

        except Exception as error:  # noqa: BLE001
            logger.warning("Memory save failed: %s", error)

        try:
            memory_extractor.extract(
                user_id=user_id,
                message=message,
                response=answer,
            )

        except Exception as error:  # noqa: BLE001
            logger.warning("Memory extraction failed: %s", error)

        try:
            if report is not None:
                knowledge.record_topic(message, user_id=user_id)

        except Exception as error:  # noqa: BLE001
            logger.debug("Topic tracking failed: %s", error)

    # ==========================================
    # Presentation
    # ==========================================

    def _decorate(self, text: str, verification, report, include_footer: bool) -> str:
        if not include_footer:
            return text

        mode = getattr(settings, "citation_mode", "auto")

        extras = []

        if mode in {"auto", "footer"} and report is not None and report.results:
            lines = []

            for result in report.results[:3]:
                if not result.url:
                    continue

                lines.append(f"- {result.source}: <{result.url}>")

            if lines:
                extras.append("-# **Sources**\n" + "\n".join(lines))

        if verification.footer():
            extras.append(verification.footer())

        if not extras:
            return text

        return text.rstrip() + "\n\n" + "\n\n".join(extras)

    # ==========================================
    # Introspection
    # ==========================================

    def last_report(self, user_id: int) -> dict | None:
        """The most recent exchange for this user, for /sources."""
        return self.reports.get(user_id)

    def health(self) -> dict:
        total = max(1, self.stats["requests"])

        return {
            **self.stats,
            "requests": self.stats["requests"],
            "grounded_rate": round(self.stats["grounded"] / total, 3),
            "search_rate": round(self.stats["searched"] / total, 3),
            "avg_seconds": round(self.stats["total_seconds"] / total, 2),
            "provider": provider_manager.name,
            "model": provider_manager.model,
        }


engine = AIEngine()
