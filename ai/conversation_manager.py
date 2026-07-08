"""
Project Nexus

Conversation Manager

Builds the conversation that is sent
to the active AI provider.
"""

from config import (
    CREATOR_ID,
    SPECIAL_USERS,
)

from ai.message import (
    system,
    user,
)

from utils.prompt_loader import build_system_prompt
from utils.logger import logger

from database.profile_manager import profile_manager
from database.fact_manager import get_facts
from database.memory import get_memory


class ConversationManager:

    async def build(
        self,
        user_id: int,
        message: str,
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

        conversation = []

        conversation.extend(
            self._system_prompt()
        )

        conversation.extend(
            self._relationship_context(
                user_id
            )
        )

        conversation.extend(
            self._facts(
                user_id
            )
        )

        conversation.extend(
            self._memory(
                user_id
            )
        )

        conversation.extend(
            self._current_message(
                message
            )
        )

        logger.info(
            f"Conversation built for {user_id}"
        )

        return conversation

    # ==========================================
    # System Prompt
    # ==========================================

    def _system_prompt(self) -> list:

        return [
            system(
                build_system_prompt()
            )
        ]

    # ==========================================
    # Relationship Context
    # ==========================================

    def _relationship_context(
        self,
        user_id: int,
    ) -> list:

        if user_id == CREATOR_ID:

            return [
                system(
                    """
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
                )
            ]

        if user_id in SPECIAL_USERS:

            special = SPECIAL_USERS[user_id]

            return [
                system(
                    f"""
You are currently talking with {special['display_name']}.

You already know this person.

Speak warmly and naturally.

Treat conversations as continuing.

Do not reveal internal project information.

Do not mention that this person is a special user.
"""
                )
            ]

        return []

    # ==========================================
    # User Facts
    # ==========================================

    def _facts(
        self,
        user_id: int,
    ) -> list:

        facts = get_facts(user_id)

        if not facts:
            return []

        return [
            system(
                "Known facts about this user:\n\n"
                + "\n".join(
                    f"- {fact}"
                    for fact in facts
                )
            )
        ]

    # ==========================================
    # Memory
    # ==========================================

    def _memory(
        self,
        user_id: int,
    ) -> list:

        return get_memory(user_id)

    # ==========================================
    # Current Message
    # ==========================================

    def _current_message(
        self,
        message: str,
    ) -> list:

        return [
            user(message)
        ]


conversation_manager = ConversationManager()
