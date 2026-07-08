"""
Project Nexus

Conversation Manager

Builds the conversation that is sent
to the active AI provider.
"""

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

        # ==========================
        # Load Profile
        # ==========================

        profile = profile_manager.get_profile(
            user_id
        )

        profile.total_messages += 1

        profile_manager.save_profile(
            profile
        )

        # ==========================
        # Load User Facts
        # ==========================

        facts = get_facts(user_id)

        # ==========================
        # Load Recent Memory
        # ==========================

        memory = get_memory(user_id)

        conversation = []

        # ==========================
        # System Prompt
        # ==========================

        conversation.append(
            {
                "role": "system",
                "content": build_system_prompt()
            }
        )

        # ==========================
        # User Facts
        # ==========================

        if facts:

            conversation.append(
                {
                    "role": "system",
                    "content":
                        "Known facts about this user:\n"
                        + "\n".join(
                            f"- {fact}"
                            for fact in facts
                        )
                }
            )

        # ==========================
        # Recent Conversation
        # ==========================

        conversation.extend(memory)

        # ==========================
        # Current User Message
        # ==========================

        conversation.append(
            {
                "role": "user",
                "content": message
            }
        )

        logger.info(
            f"Conversation built for {user_id}"
        )

        return conversation


conversation_manager = ConversationManager()
