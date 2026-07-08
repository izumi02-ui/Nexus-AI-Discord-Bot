"""
Project Nexus

Conversation Manager

Builds the conversation that is sent
to the active AI provider.
"""

from utils.prompt_loader import build_system_prompt
from utils.logger import logger

from database.profile_manager import profile_manager


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

        # Load user profile
        profile = profile_manager.get_profile(
            user_id
        )

        # Update statistics
        profile.total_messages += 1

        # Save updated profile
        profile_manager.save_profile(profile)

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

        if profile.facts:

            facts = "\n".join(
                f"- {fact}"
                for fact in profile.facts
            )

            conversation.append(
                {
                    "role": "system",
                    "content": (
                        "Known facts about this user:\n"
                        f"{facts}"
                    )
                }
            )

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
