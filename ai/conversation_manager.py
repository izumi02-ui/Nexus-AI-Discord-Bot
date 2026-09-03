"""
Project Nexus

Conversation Manager

Builds the conversation that is sent
to the active AI provider.

Ordering matters as much as content: the persona first (so it survives any
later truncation), then who the user is to Nexus, then what Nexus knows about
that person, then verified external evidence, then the recent exchange, then
the message itself. When the budget runs short, whole blocks are dropped by
priority - never the middle of a conversation, which is what makes a model
forget what it was just told.
"""

from ai.message import (
    system,
    user,
)

from config import (
    CREATOR_ID,
    SPECIAL_USERS,
)

from database.fact_manager import relevant_facts
from database.memory import get_memory
from database.profile_manager import profile_manager

from utils.logger import logger
from utils.prompt_loader import build_system_prompt
from utils.settings import settings

#: Rough character ceiling for the whole prompt. 26k is about 7-8k tokens,
#: which every provider Nexus runs on (including the free ones) accepts.
CHAR_BUDGET = 26_000

MAX_MEMORY_MESSAGES = 12

PRIORITY_PERSONA = 0
PRIORITY_EVIDENCE = 1
PRIORITY_MEMORY_FACTS = 2
PRIORITY_NOTES = 3


class ConversationManager:

    async def build(
        self,
        user_id: int,
        message: str,
        *,
        report=None,
        remembered: list | None = None,
        context_note: str | None = None,
        retry_instruction: str | None = None,
        include_memory: bool = True,
    ) -> list:
        """
        Build the complete AI conversation.
        """

        logger.info(
            f"Building conversation for {user_id}"
        )

        profile = profile_manager.get_profile(
            user_id
        )

        profile.total_messages += 1

        profile_manager.save_profile(
            profile
        )

        blocks: list[tuple[int, str]] = [
            (PRIORITY_PERSONA, build_system_prompt()),
        ]

        relationship = self._relationship_context(user_id)

        if relationship:
            blocks.append((PRIORITY_PERSONA, relationship))

        if retry_instruction:
            blocks.append((PRIORITY_PERSONA, retry_instruction))

        if report is not None:
            evidence = self._evidence(report)

            if evidence:
                blocks.append((PRIORITY_EVIDENCE, evidence))

        verified = self._verified_knowledge(remembered or [], report)

        if verified:
            blocks.append((PRIORITY_EVIDENCE + 1, verified))

        facts = self._facts(user_id, message)

        if facts:
            blocks.append((PRIORITY_MEMORY_FACTS, facts))

        if context_note:
            blocks.append((PRIORITY_NOTES, context_note))

        conversation = [system(content) for _priority, content in blocks]

        if include_memory:
            conversation += self._memory(user_id)

        conversation.append(user(message))

        return self._fit(conversation, blocks)

    # ==========================================
    # Relationship Context
    # ==========================================

    def _relationship_context(
        self,
        user_id: int,
    ) -> str | None:

        if user_id == CREATOR_ID:

            return """
You are currently talking with Rohit.

Rohit is the creator of Project Nexus.

You already know him well because you've worked together on Project Nexus.

Treat conversations as continuing rather than first meetings.

Speak naturally.

You may greet him by name occasionally.

Do not repeatedly mention that he is the creator.

Only mention his creator role when it is relevant.

Never become overly formal.
"""

        if user_id in SPECIAL_USERS:

            special = SPECIAL_USERS[user_id]

            return f"""
You are currently talking with {special['display_name']}.

You already know this person.

Speak warmly and naturally.

Treat conversations as continuing.

Do not reveal internal project information.

Do not mention that this person is a special user.
"""

        return None

    # ==========================================
    # User Facts
    # ==========================================

    def _facts(
        self,
        user_id: int,
        message: str,
    ) -> str | None:

        facts = relevant_facts(user_id, message)

        if not facts:
            return None

        return (
            "What you remember about this user. These are things they told "
            "you, not verified outside facts.\n\n"
            + "\n".join(
                f"- {fact}"
                for fact in facts
            )
            + "\n\nUse them only where relevant. If one conflicts with what "
            "the user says now, the newer statement wins: Nexus updates its "
            "memory instead of arguing with someone about their own life."
        )

    # ==========================================
    # Verified Knowledge (self-updating store)
    # ==========================================

    def _verified_knowledge(self, rows: list, report=None) -> str | None:
        """
        Fresh, previously verified answers - with their shelf life attached.

        Suppressed when live evidence for the same question is already in the
        prompt: the newest source always outranks a stored note.
        """
        if not rows or (report is not None and getattr(report, "results", None)):
            return None

        from utils.time_utils import humanize_age

        lines = [
            "Facts Nexus verified earlier and re-checks on a schedule. "
            "Use them only if they still answer the question, and say when "
            "you are relying on a stored note rather than a fresh lookup."
        ]

        for row in rows:
            provenance = row.get("source") or "unknown source"

            if row.get("url"):
                provenance += f" - {row['url']}"

            entry = f"- {row['value']}"

            entry += f"\n  verified {humanize_age(row.get('verified_at'))} via {provenance}"

            if row.get("status") == "disputed":
                entry += (
                    "\n  DISPUTED: sources contradicted each other. Do not "
                    "state this as fact; say it is unresolved."
                )

            lines.append(entry)

        return "\n".join(lines)

    # ==========================================
    # Evidence
    # ==========================================

    def _evidence(self, report) -> str | None:
        return report.as_context(
            max_items=getattr(settings, "max_context_sources", 5),
            char_budget=getattr(settings, "evidence_char_budget", 9000),
        ) or None

    # ==========================================
    # Memory
    # ==========================================

    def _memory(
        self,
        user_id: int,
    ) -> list:

        rows = get_memory(user_id) or []

        # The current message is appended separately, so drop a trailing
        # duplicate if a previous save wrote it already.
        return rows[-MAX_MEMORY_MESSAGES:]

    # ==========================================
    # Budget
    # ==========================================

    def _fit(self, conversation: list, blocks: list) -> list:
        """
        Enforce the character budget by dropping whole blocks, least important
        first (notes, then user facts, then evidence). The persona and the
        question itself are never dropped.
        """
        total = sum(len(entry.get("content") or "") for entry in conversation)

        if total <= CHAR_BUDGET:
            return conversation

        overflow = total - CHAR_BUDGET

        # Blocks whose text matches, sorted by descending priority.
        droppable = sorted(
            (
                (priority, content)
                for priority, content in blocks
                if priority > PRIORITY_PERSONA
            ),
            key=lambda item: -item[0],
        )

        for priority, content in droppable:
            if overflow <= 0:
                break

            conversation = [
                entry for entry in conversation if entry.get("content") != content
            ]

            overflow -= len(content)

            logger.info(
                "Prompt over budget: dropped a %s-priority block (%s chars)",
                priority,
                len(content),
            )

        # Still too big: trim the oldest memory turns, keep the persona.
        if overflow > 0:
            while overflow > 0 and len(conversation) > 3:
                removed = conversation.pop(1)

                overflow -= len(removed.get("content") or "")

        return conversation

    # ==========================================
    # Introspection
    # ==========================================

    def preview(self, conversation: list) -> dict:
        return {
            "blocks": len(conversation),
            "characters": sum(len(entry.get("content") or "") for entry in conversation),
            "roles": [entry.get("role") for entry in conversation],
        }


conversation_manager = ConversationManager()
