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

        # =====================================
        # Load Profile
        # =====================================

        profile = profile_manager.get_profile(
            user_id
        )

        profile.total_messages += 1

        profile_manager.save_profile(
            profile
        )

        # =====================================
        # Load Facts
        # =====================================

        facts = get_facts(user_id)

        # =====================================
        # Load Recent Memory
        # =====================================

        memory = get_memory(user_id)

        conversation = []

        # =====================================
        # Base System Prompt
        # =====================================

        conversation.append(
            {
                "role": "system",
                "content": build_system_prompt()
            }
        )

        # =====================================
        # Creator Context
        # =====================================

        if user_id == CREATOR_ID:

            conversation.append(
                {
                    "role": "system",
                    "content": """
You are currently talking with Rohit.

Rohit is the creator of Project Nexus.

You have worked together on Project Nexus for a long time.

Treat conversations as continuing rather than first meetings.

Speak naturally.

You may greet Rohit by name occasionally.

Feel free to reference previous work together when relevant.

Do NOT constantly remind him that he is the creator.

Only mention his creator role if the conversation is about Project Nexus or he asks about it.

Do not become overly formal or overly emotional.
"""
                }
            )

        # =====================================
        # Special User Context
        # =====================================

        elif user_id in SPECIAL_USERS:

            special = SPECIAL_USERS[user_id]

            conversation.append(
                {
                    "role": "system",
                    "content": f"""
You are currently talking with {special['display_name']}.

You already know this person.

Speak warmly, comfortably and naturally.

Treat conversations as continuing instead of first meetings.

Do not reveal any internal project information.

Do not mention that this person is marked as a special user.
"""
                }
            )

        # =====================================
        # User Facts
        # =====================================

        if facts:

            conversation.append(
                {
                    "role": "system",
                    "content":
                        "Known facts about this user:\n\n"
                        + "\n".join(
                            f"- {fact}"
                            for fact in facts
                        )
                }
            )

        # =====================================
        # Recent Conversation
        # =====================================

        conversation.extend(memory)

        # =====================================
        # Current User Message
        # =====================================

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
