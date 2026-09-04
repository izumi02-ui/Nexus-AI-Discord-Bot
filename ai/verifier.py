"""
Project Nexus

Answer Verifier

The last gate before a reply is sent.

Given the model's draft and the evidence that was supposed to back it, the
verifier answers one question: *is Nexus allowed to say this?*

  * a link the model quoted that no tool returned is removed - a fabricated
    URL is the single most damaging thing an assistant can send;
  * a time-sensitive answer built on nothing triggers a retry with search, or
    a refusal when the operator prefers honesty over confidence;
  * a reply that repeats a model's "I can't browse the internet" excuse gets
    rewritten, because Nexus can;
  * disagreement between sources, a single source, or a cached answer are
    disclosed to the user instead of hidden.

Nothing here tries to make the answer *sound* verified; it either grounds the
claim or lowers Nexus' confidence out loud.
"""

import re
from dataclasses import dataclass, field

from search.query import domain_of
from utils.logger import logger
from utils.settings import settings

URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)

# Some instruction-tuned models imitate a tool protocol in plain text instead
# of returning an answer.  Nexus does retrieval before the model call, so this
# markup is never useful to a user and must never reach Discord.
TOOL_PROTOCOL_RE = re.compile(
    r"(?:"
    r"</?(?:tool_call|arg_key|arg_value|function_call|function)[^>]*>"
    r"|\[\s*/?\s*(?:tool[_ -]?call|function[_ -]?call)\s*\]"
    r"|(?:^|\n)\s*(?:tool[_ -]?call|function[_ -]?call)\s*[:=]"
    r")",
    re.IGNORECASE,
)

MONEY_RE = re.compile(r"[$€£₹]\s?\d[\d,]*(?:\.\d+)?\s?(?:billion|million|trillion|bn)?", re.IGNORECASE)

PERCENT_RE = re.compile(r"\b\d{1,4}(?:\.\d+)?\s?(?:%|percent)\b", re.IGNORECASE)

#: A stated quantity with a unit or a decimal is a checkable claim, even when
#: it is not money: "27.4 million people", "1 340 km", "9.7 °C".
MEASURE_RE = re.compile(
    r"\b\d{1,3}(?:[.,]\d{3})+(?:\.\d+)?\b"          # 1,234 / 27.4 / 12.500
    r"|\b\d+(?:\.\d+)?\s?(?:million|billion|trillion|thousand|km|kg|mi|mph|kph|mb|gb|tb|px|°[cf]|m|cm|mm|kg|tonnes?)\b",
    re.IGNORECASE,
)

CUTOFF_PATTERNS = (
    r"my (?:training|knowledge) (?:data |cutoff )?(?:ends|stopped|is limited)",
    r"as of my (?:last|final) (?:training|knowledge|update)",
    r"i (?:can'?t|cannot|don'?t have|do not have|am not able to|am unable to) "
    r"(?:access|browse|search|check|see|reach)[^.]{0,40}(?:internet|web|online|today|current)",
    r"i (?:don'?t|do not) (?:have )?access to (?:real[- ]time|current|live) (?:data|information)",
    r"my knowledge (?:cut|cutoff)",
    r"i (?:can'?t|cannot) (?:confirm|verify) (?:that )?without (?:a |an )?(?:search|web|browsing)",
)

UNCERTAIN_RE = re.compile(
    r"\b(?:i believe|approximately|around|about|roughly|as far as i know|"
    r"i think|probably|likely)\b",
    re.IGNORECASE,
)

ABSOLUTE_RE = re.compile(
    r"\b(?:is|are|was|were|has|have|will|stands at|sits at|currently)\b",
    re.IGNORECASE,
)

STRONG_CLAIM_RE = re.compile(
    r"\b(?:definitely|certainly|guaranteed|100%|without a doubt|it is a fact)\b",
    re.IGNORECASE,
)


@dataclass
class Verification:

    answer: str

    grounded: bool = False

    confidence: float = 0.0

    issues: list[str] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)

    removed_urls: list[str] = field(default_factory=list)

    needs_retry: bool = False

    refused: bool = False

    #: figures the answer asserted that no source contained
    unverified_figures: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.grounded

    @property
    def summary(self) -> str:
        parts = []

        if self.grounded:
            parts.append("verified")
        else:
            parts.append("unverified")

        parts.append(f"confidence {self.confidence:.2f}")

        if self.issues:
            parts.append("; ".join(self.issues[:3]))

        return " · ".join(parts)

    def footer(self) -> str | None:
        """Small Discord-side note under the answer, when one is warranted."""
        lines = []

        if self.notes:
            lines.append("-# ⚠️ " + " · ".join(self.notes[:2]))

        if not lines:
            return None

        return "\n".join(lines)


class AnswerVerifier:

    # ==========================================
    # Public API
    # ==========================================

    def verify(
        self,
        *,
        query: str,
        answer: str,
        report=None,
        freshness: str | None = None,
        knowledge_rows: list | None = None,
        allow_retry: bool = True,
    ) -> Verification:
        from search.freshness import classify

        freshness = freshness or classify(query)

        results = list(getattr(report, "results", []) or [])

        verification = Verification(
            answer=(answer or "").strip(),
            confidence=float(
                getattr(report, "cross", {}).get("top_confidence", 0.0)
            )
            if results
            else 0.0,
        )

        if not verification.answer:
            verification.answer = "I could not put together an answer for that."
            verification.grounded = True

            return verification

        self._check_tool_protocol(verification, allow_retry=allow_retry)
        self._strip_fabricated_links(verification, results)
        self._check_numbers(verification, query, results, freshness)
        self._check_cutoff_excuses(verification, results, freshness)
        self._check_grounding(
            verification,
            results,
            freshness,
            knowledge_rows,
            report=report,
            allow_retry=allow_retry,
        )
        self._disclose(report, verification, results, knowledge_rows)

        if verification.refused:
            verification.answer = self.refusal_text(query, report)

        if not getattr(settings, "verification_enabled", True):
            verification.grounded = True
            verification.needs_retry = False
            verification.notes = []

        return verification

    # ==========================================
    # Checks
    # ==========================================

    def _check_tool_protocol(
        self,
        verification: Verification,
        *,
        allow_retry: bool,
    ) -> None:
        """Reject model-generated tool syntax instead of exposing it."""
        if not TOOL_PROTOCOL_RE.search(verification.answer):
            return

        verification.issues.append("model emitted unevaluated tool-call markup")
        verification.grounded = False
        verification.confidence = 0.0

        if allow_retry and getattr(settings, "auto_retry_with_search", True):
            verification.needs_retry = True
        else:
            # A retry has already been spent (or retries are disabled).  A
            # short refusal is safer than displaying internal-looking syntax.
            verification.refused = True

    @staticmethod
    def _canon(url: str) -> str:
        """Compare URLs the way a human reads them, not byte for byte."""
        url = (url or "").strip().rstrip(".,);]}'\"")

        url = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
        url = re.sub(r"^www\.", "", url, flags=re.IGNORECASE)

        return url.rstrip("/").lower()

    def _strip_fabricated_links(self, verification: Verification, results):
        """
        Remove URLs that no tool actually returned.

        Model-invented citations look *more* trustworthy than no citation, so
        this is a hard filter rather than a warning.
        """
        urls = set(URL_RE.findall(verification.answer))

        if not urls:
            return

        allowed = set()

        for result in results:
            for value in (
                result.url,
                result.metadata.get("homepage"),
                result.image,
                result.video,
            ):
                if value:
                    allowed.add(self._canon(value))

            for value in URL_RE.findall(result.content or ""):
                allowed.add(self._canon(value))

        stripped = []
        removed = []

        for url in urls:
            if self._canon(url) in allowed:
                continue

            removed.append(url)
            stripped.append(url)

        if not stripped:
            return

        for url in stripped:
            # Markdown link -> plain text; bare URL -> deleted.
            verification.answer = re.sub(
                r"\[([^\]]{1,120})\]\(" + re.escape(url) + r"\)",
                r"\1",
                verification.answer,
            )
            verification.answer = verification.answer.replace(url, "")

        verification.answer = re.sub(r"[ \t]{2,}", " ", verification.answer)
        verification.answer = re.sub(r"[ \t]+(\n|$)", r"\1", verification.answer)

        # Removing a link must not leave "See " or "()" behind.
        verification.answer = re.sub(r"\(\s*\)", "", verification.answer)
        verification.answer = re.sub(
            r"[ \t]*(?:see|source|link|here|read more|more info|details)"
            r"[ \t]*[:\-]?[ \t]*$",
            "",
            verification.answer,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        verification.answer = re.sub(r"[ \t]{2,}", " ", verification.answer)
        verification.answer = re.sub(r" +([.,;:!?])", r"\1", verification.answer)
        verification.answer = verification.answer.strip()

        verification.removed_urls = removed
        verification.issues.append(
            f"removed {len(stripped)} unverified link(s)"
        )

        logger.warning(
            "Verifier removed %s fabricated link(s) from an answer: %s",
            len(stripped),
            ", ".join(removed[:3]),
        )

    def _check_numbers(self, verification: Verification, query, results, freshness):
        """
        Numbers must come from somewhere.

        Only enforced for time-sensitive questions that did have evidence -
        otherwise a poem with "3" in it gets audited.
        """
        if not results or freshness not in {"instant", "short", "medium"}:
            return

        evidence = " ".join(result.content or "" for result in results)

        missing = []

        for pattern, name in (
            (MONEY_RE, "price"),
            (PERCENT_RE, "percentage"),
            (MEASURE_RE, "figure"),
        ):
            seen = set()

            for match in pattern.finditer(verification.answer):
                token = match.group(0).strip()

                if not token or token in seen:
                    continue

                seen.add(token)

                number = re.sub(r"[^\d.]", "", token)

                if number and number in evidence:
                    continue

                missing.append(f"{name} {token}")

        if missing:
            verification.unverified_figures = missing

            verification.issues.append(
                f"{len(missing)} figure(s) not present in the evidence"
                f" ({', '.join(missing[:2])})"
            )
            verification.notes.append(
                "some figures could not be matched to a source"
            )
            verification.confidence = min(verification.confidence, 0.6)

    def _check_cutoff_excuses(self, verification: Verification, results, freshness):
        """
        Nexus is not a chatbot with no internet: it has tools.

        When the model claims it cannot check, the answer is re-asked with the
        evidence wired in; if a retry was already used, the excuse is stripped
        so the user is not told something false about the bot.
        """
        pattern = "|".join(CUTOFF_PATTERNS)

        if not re.search(pattern, verification.answer, re.IGNORECASE):
            return

        verification.issues.append("model claimed it cannot check live information")

        sentence_split = re.split(r"(?<=[.!?])\s+", verification.answer)

        kept = [
            sentence
            for sentence in sentence_split
            if not re.search(pattern, sentence, re.IGNORECASE)
        ]

        verification.answer = " ".join(kept).strip() or verification.answer

        if freshness in {"instant", "short"} or results:
            verification.needs_retry = True

    def _check_grounding(
        self,
        verification: Verification,
        results,
        freshness,
        knowledge_rows,
        *,
        report=None,
        allow_retry: bool = True,
    ):
        """
        Decide whether the answer may stand as-is.

        "Grounded" means an independent source actually supports it - not that
        a source merely exists. A single domain, a contradicted stored note, or
        a figure no evidence contains all demote the answer to unverified, and
        time-sensitive ones then get exactly one repair attempt.
        """
        min_sources = int(getattr(settings, "min_sources_for_grounding", 1) or 1)

        cross = dict(getattr(report, "cross", {}) or {})

        domains = {
            (result.domain or domain_of(result.url or ""))
            for result in results
        }

        domains.discard("")

        independent = len(domains) or int(cross.get("sources") or 0)

        disputed = [
            row
            for row in (knowledge_rows or [])
            if str(row.get("status", "")).lower() == "disputed"
        ]

        report_grounded = (
            bool(results)
            and independent >= min_sources
            and not cross.get("conflicts")
        )

        knowledge_grounded = bool(
            knowledge_rows
            and not disputed
            and freshness not in {"instant", "short"}
        )

        verification.grounded = bool(
            report_grounded or knowledge_grounded or freshness == "static"
        )

        if disputed:
            verification.issues.append(
                f"{len(disputed)} stored note(s) conflict with this question"
            )
            verification.confidence = min(verification.confidence, 0.6)

        if verification.grounded and not verification.unverified_figures:
            return

        time_sensitive = freshness in {"instant", "short"}

        if not self._states_something_checkable(verification):
            if (
                time_sensitive
                and not verification.grounded
                and allow_retry
                and getattr(settings, "auto_retry_with_search", True)
            ):
                verification.needs_retry = True
                return

            if (
                time_sensitive
                and not verification.grounded
                and getattr(settings, "refuse_when_unverified", False)
            ):
                verification.refused = True
                return

            # The model already hedged: for non-live questions that is an
            # honest answer and can stand with a low confidence marker.
            verification.issues.append("answered without evidence, hedged")
            verification.confidence = min(verification.confidence, 0.45)

            return

        if not verification.grounded:
            verification.issues.append("stated a current fact with no evidence")
            verification.confidence = min(verification.confidence, 0.4)

        if (time_sensitive and not verification.grounded) or verification.unverified_figures:
            if allow_retry and getattr(settings, "auto_retry_with_search", True):
                verification.needs_retry = True
            elif getattr(settings, "refuse_when_unverified", False):
                verification.refused = True
            else:
                verification.notes.append(
                    "not verified against a live source"
                )

    @staticmethod
    def _states_something_checkable(verification: Verification) -> bool:
        """
        Did the answer assert something a source could contradict?

        Hedged prose ("I believe roughly ...") is allowed to stand without
        evidence. The moment it contains a price, a percentage or a count, or
        cites a link the verifier had to delete, it is a claim - and a claim
        either has a source or gets checked again.
        """
        if verification.unverified_figures or verification.removed_urls:
            return True

        answer = verification.answer

        concrete = bool(
            MONEY_RE.search(answer)
            or PERCENT_RE.search(answer)
            or re.search(r"\b\d{1,3}(?:[.,]\d{3})+(?:\.\d+)?\b", answer)
            or re.search(r"\b\d+(?:\.\d+)?\s(?:million|billion|trillion|kg|km|mb|gb|px)\b", answer, re.IGNORECASE)
        )

        if concrete:
            return True

        absolute = bool(ABSOLUTE_RE.search(answer)) or bool(
            STRONG_CLAIM_RE.search(answer)
        )

        return bool(absolute and not UNCERTAIN_RE.search(answer))

    def _disclose(self, report, verification: Verification, results, knowledge_rows):
        """Everything the user should know about how solid this is."""
        cross = getattr(report, "cross", {}) or {}

        if report is not None and getattr(report, "from_cache", False):
            verification.notes.append("answered from cached sources")

        if cross.get("conflicts"):
            conflict = cross["conflicts"][0]

            verification.notes.append(
                "sources disagree on "
                + conflict.get("kind", "the figures")
                + " ("
                + " vs ".join(conflict.get("values", [])[:2])
                + ")"
            )

        domains = cross.get("domains") or []

        if results and len(domains) <= 1:
            verification.notes.append("only one independent source was found")

        if knowledge_rows and not results:
            verification.notes.append(
                "answered from Nexus' verified notes"
            )

        if verification.unverified_figures:
            verification.notes.append(
                "figures not confirmed by a source: "
                + ", ".join(verification.unverified_figures[:2])
            )

    # ==========================================
    # Retry support
    # ==========================================

    def reask_instruction(self, verification: Verification) -> str:
        """The extra system line used when Nexus re-asks itself."""
        return (
            "Your previous answer could not be supported by evidence. "
            "Answer again using ONLY the evidence supplied in this prompt. "
            "If the evidence does not cover the question, say precisely which "
            "part you cannot confirm. Do not mention your training data, and "
            "do not cite any link that is not written above. Return only the "
            "final natural-language answer. Never output <tool_call>, "
            "[TOOL_CALL], <arg_key>, <arg_value>, JSON tool requests, or instructions for "
            "another tool to run."
        )

    def refusal_text(self, query: str, report) -> str:
        sources = getattr(report, "tools_used", []) or []

        tail = (
            f" I tried {', '.join(sources[:3])} and got nothing usable."
            if sources
            else ""
        )

        return (
            "I could not verify that right now, so I would rather not guess."
            + tail
            + " Try narrowing the question, or ask me to search a specific site."
        )


verifier = AnswerVerifier()
