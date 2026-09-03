"""
Project Nexus

Memory Extractor

Extracts long-term facts from conversations.

Three ways a fact enters memory:

  1. the user asks for it directly ("remember that ...", "note: ...");
  2. a rule matches something durable about them (name, where they live, ...);
  3. optionally, the model is asked to summarise what is worth keeping -
     off by default because it costs an extra call per message.

Corrections are handled explicitly: "actually, my name is X" replaces the
stored name instead of adding a second one. Facts that came from the *model*
are never stored as truth - only what the user said about themselves.
"""

import asyncio
import json
import re

from ai.message import system, user as user_message

from database.fact_manager import (
    clear_facts,
    delete_fact,
    find,
    get_facts,
    remember_fact,
    stats as fact_stats,
)

from utils.logger import logger
from utils.settings import settings

CATEGORY_RE = re.compile(r"^\s*(?:note|remember|fact)\s*[:\-]\s*(.+)$", re.IGNORECASE)

DIRECTIVE_RE = re.compile(
    r"""(?:\b(?:please\s+)?(?:remember|note|keep\s+in\s+mind|memori[sz]e|store|save)\b)
        \s+(?:that\s+)?(?P<fact>.{3,240})""",
    re.IGNORECASE | re.VERBOSE,
)

CORRECTION_RE = re.compile(
    r"(?:\b(?:actually|no[, ]+actually|wait|correction|instead|rather)\b[,: ]+)?"
    r"\b(?:my|the)\s+(?P<subject>name|age|birthday|location|city|country|school|job|"
    r"occupation|timezone|pronouns?|language|project|stack|editor)\s+"
    r"(?:is|are|used\s+to\s+be)\s+(?P<value>.{1,120})",
    re.IGNORECASE,
)

SUBJECT_TO_CATEGORY = {
    "name": "Name",
    "age": "Age",
    "birthday": "Birthday",
    "location": "Lives in",
    "city": "Lives in",
    "country": "From",
    "school": "Studies",
    "job": "Occupation",
    "occupation": "Occupation",
    "timezone": "Timezone",
    "pronoun": "Pronouns",
    "pronouns": "Pronouns",
    "language": "Speaks",
    "project": "Project",
    "stack": "Stack",
    "editor": "Editor",
}

# (regex, category) - a leading "not/never" marks removal instead of storage.
RULES = [
    (re.compile(r"\bmy name is\s+(?P<v>[A-Za-z][A-Za-z .'-]{1,40})", re.I), "Name"),
    (re.compile(r"\bi am(?:'m)? called\s+(?P<v>[A-Za-z][A-Za-z .'-]{1,40})", re.I), "Name"),
    (re.compile(r"\bcall me\s+(?P<v>[A-Za-z][A-Za-z .'-]{1,30})", re.I), "Name"),
    (re.compile(r"\bi(?:'m| am)\s+(?P<v>\d{1,2})\s+years?\s+old", re.I), "Age"),
    (re.compile(r"\bi(?:'m| am)\s+from\s+(?P<v>[A-Za-z][A-Za-z ,.'-]{1,60})", re.I), "From"),
    (re.compile(r"\bi live in\s+(?P<v>[A-Za-z][A-Za-z ,.'-]{1,60})", re.I), "Lives in"),
    (re.compile(r"\bi(?:'m| am) (?:currently )?based in\s+(?P<v>[A-Za-z][A-Za-z ,.'-]{1,60})", re.I), "Lives in"),
    (re.compile(r"\bi (?:study|am studying)\s+(?P<v>[A-Za-z][A-Za-z ,.&'-]{1,60})", re.I), "Studies"),
    (re.compile(r"\bi work (?:as|at)\s+(?P<v>.{2,60})", re.I), "Occupation"),
    (re.compile(r"\bi(?:'m| am) (?:a|an)\s+(?P<v>(?:software|data|front|back|full)[a-z ]*developer|student|designer|teacher|engineer|programmer)", re.I), "Occupation"),
    (re.compile(r"\bi(?:'m| am) learning\s+(?P<v>[A-Za-z#+.][A-Za-z0-9#+. -]{1,40})", re.I), "Learning"),
    (re.compile(r"\bmy favorite\s+(?P<v>[a-z ]{2,30}?)\s+is\s+(?P<w>[A-Za-z0-9][A-Za-z0-9 .:&'-]{1,60})", re.I), None),
    (re.compile(r"\bi (?:love|like|enjoy)\s+(?P<v>[A-Za-z0-9][A-Za-z0-9 .:&'-]{2,60})\b", re.I), "Likes"),
    (re.compile(r"\bi (?:hate|dislike)\s+(?P<v>[A-Za-z0-9][A-Za-z0-9 .:&'-]{2,60})\b", re.I), "Dislikes"),
    (re.compile(r"\bmy pronouns? (?:are|is)\s+(?P<v>[A-Za-z/-]{2,25})", re.I), "Pronouns"),
    (re.compile(r"\bi use\s+(?P<v>[A-Za-z0-9][A-Za-z0-9 .#+-]{2,50})\b", re.I), "Uses"),
    (re.compile(r"\bmy time\s?zone is\s+(?P<v>[A-Za-z0-9/ +-]{2,30})", re.I), "Timezone"),
    (re.compile(r"\bi(?:'m| am) (?:online|active) (?:mostly )?(?:between|from)\s+(?P<v>\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:-|to|–)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", re.I), "Active hours"),
]

FORGET_RE = re.compile(
    r"(?:\b(?:forget|delete|remove|ignore)\b)\s+(?:that\s+|about\s+|everything\s+(?:about|regarding)\s+)?(?P<v>.{2,120})",
    re.IGNORECASE,
)

NEGATED_RE = re.compile(r"\b(?:don'?t|do not|never|stop|no longer|not)\b", re.IGNORECASE)

EXTRACTION_PROMPT = """You maintain Nexus' long-term memory.

Given the latest exchange, list durable facts worth remembering FOREVER about
the USER only. Durable means stable over months: name, where they live, what
they study or build, preferences, time zone, standing projects.

Ignore: current mood, one-off questions, temporary plans, anything about
other people, and anything the assistant said.

Reply with JSON only:
{"facts": [{"category": "Name", "value": "Rohit"}], "forget": ["old claim"]}
Use an empty list when there is nothing durable."""


class MemoryExtractor:

    # ==========================================
    # Entry point
    # ==========================================

    def extract(
        self,
        user_id: int,
        message: str,
        response: str = "",
    ) -> list[dict]:
        """
        Pull durable facts out of one user message.

        Returns the recorded actions, which callers surface in commands.
        """
        logger.info(
            f"Extracting memory for {user_id}"
        )

        text = (message or "").strip()

        if not text:
            return []

        actions = []

        actions += self._handle_forget(user_id, text)
        actions += self._handle_directive(user_id, text)
        actions += self._handle_correction(user_id, text)
        actions += self._handle_rules(user_id, text)

        if not actions and getattr(settings, "memory_llm_extraction", False):
            self._schedule_llm(user_id, text, response)

        if not actions:
            logger.info(
                "No new facts found."
            )

        return actions

    # ==========================================
    # Rules
    # ==========================================

    def _handle_forget(self, user_id: int, text: str) -> list[dict]:
        actions = []

        for match in FORGET_RE.finditer(text):
            target = match.group("v").strip(" ?!.")

            if not target or len(target) < 2:
                continue

            # "forget what you know about me" style requests.
            if re.fullmatch(r"(?:everything|all of it|it|my info|my facts?)", target, re.I):
                before = fact_stats(user_id).get("active", 0) or 0

                clear_facts(user_id)

                actions.append({"action": "cleared", "removed": before})

                logger.info("Cleared all stored facts for %s", user_id)

                continue

            removed = delete_fact(user_id, target)

            actions.append(
                {
                    "action": "forgotten",
                    "target": target,
                    "removed": removed,
                }
            )

            if removed:
                logger.info("Forgot %s fact(s) matching %r", removed, target)

        return actions

    def _handle_directive(self, user_id: int, text: str) -> list[dict]:
        """Explicit "remember that ..." / "note: ..." requests."""
        actions = []

        for pattern in (CATEGORY_RE, DIRECTIVE_RE):
            for match in pattern.finditer(text):
                if pattern is CATEGORY_RE:
                    fact = match.group(1)
                else:
                    fact = match.group("fact")

                    # Do not double-handle the same sentence.
                    if re.search(r"(?:remember|note|keep in mind|memorise|memorize)\b[:\-]?\s*$",
                                 text[: match.start()], re.I):
                        continue

                if NEGATED_RE.search(fact) and not re.search(r"never", fact, re.I):
                    continue

                result = remember_fact(
                    user_id,
                    fact.strip(" ?!."),
                    source="explicit request",
                )

                if result.get("action") in {"added", "replaced", "unchanged"}:
                    actions.append(result)

                break

        return actions

    def _handle_correction(self, user_id: int, text: str) -> list[dict]:
        """"Actually my name is X" - replace the stored value, don't add one."""
        if not re.search(r"\b(actually|correction|instead|rather|no,)\b", text, re.I):
            return []

        actions = []

        for match in CORRECTION_RE.finditer(text):
            subject = match.group("subject").lower()
            value = match.group("value").strip(" .,!?")

            category = SUBJECT_TO_CATEGORY.get(subject, subject.title())

            if not value:
                continue

            actions.append(
                remember_fact(
                    user_id,
                    f"{category}: {value}",
                    category=category,
                    source="correction",
                )
            )

        return actions

    def _handle_rules(self, user_id: int, text: str) -> list[dict]:
        """
        Pattern-based extraction, one stored fact per category per message.

        Negations remove instead of add: "I don't like Minecraft any more" must
        not be filed as a preference.
        """
        actions = []

        head = re.split(r"[.!?]", text)[0]

        for pattern, category in RULES:
            match = pattern.search(head) or pattern.search(text)

            if not match:
                continue

            if category is None:
                label = (match.group("v").strip().title() or "Favorite")

                value = match.group("w").strip(" .,!?")

                fact_value = f"Favorite {label}: {value}"
            else:
                fact_value = f"{category}: {match.group('v').strip(' .,!?')}"

            if len(fact_value.split(":", 1)[-1].strip()) < 2:
                continue

            if NEGATED_RE.search(text[: match.start() + 40]):
                from database.fact_manager import delete_fact

                removed = delete_fact(user_id, fact_value.split(":", 1)[0])

                if removed:
                    actions.append(
                        {"action": "forgotten", "target": fact_value, "removed": removed}
                    )

                continue

            actions.append(
                remember_fact(
                    user_id,
                    fact_value,
                    category=(category or "Favorite"),
                    source="conversation",
                )
            )

            break

        return actions

    # ==========================================
    # Optional model-assisted extraction
    # ==========================================

    def _schedule_llm(self, user_id: int, text: str, response: str):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        loop.create_task(self._llm_extract(user_id, text, response))

    async def _llm_extract(self, user_id: int, text: str, response: str):
        """
        Ask the model for structured facts, then store only what it returns.

        Never trusts the model's phrasing as a fact about the world - it is
        only used to decide *what* of the user's message is worth keeping.
        """
        if len(text) < 30:
            return

        try:
            from ai.provider_manager import provider_manager

            conversation = [
                system(EXTRACTION_PROMPT),
                user_message(
                    f"USER: {text[:1500]}\n\nNEXUS: {(response or '')[:700]}"
                ),
            ]

            raw = await provider_manager.ask(
                user_id=user_id,
                conversation=conversation,
            )
        except Exception as error:  # noqa: BLE001 - memory is best effort
            logger.debug("LLM memory extraction skipped: %s", error)

            return

        payload = self._parse_json(raw)

        if not payload:
            return

        for item in payload.get("facts", [])[:4]:
            if not isinstance(item, dict):
                continue

            value = str(item.get("value", "")).strip()

            if not value or len(value) > 160:
                continue

            remember_fact(
                user_id,
                value,
                category=str(item.get("category") or "Note")[:30],
                source="model extraction",
                confidence=0.75,
            )

        for term in payload.get("forget", [])[:3]:
            from database.fact_manager import delete_fact

            if isinstance(term, str) and term.strip():
                delete_fact(user_id, term.strip())

    def _parse_json(self, raw: str) -> dict | None:
        text = (raw or "").strip()

        fence = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)

        if fence:
            text = fence.group(1).strip()

        start, end = text.find("{"), text.rfind("}")

        if start == -1 or end <= start:
            return None

        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

        return data if isinstance(data, dict) else None

    # ==========================================
    # Review
    # ==========================================

    def review(self, user_id: int) -> dict:
        """What memory currently holds, for the audit command."""
        return {
            "facts": get_facts(user_id, limit=40),
            "stats": fact_stats(user_id),
        }


memory_extractor = MemoryExtractor()
