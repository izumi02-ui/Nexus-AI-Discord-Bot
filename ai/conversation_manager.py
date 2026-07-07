"""
Project Nexus

Conversation Manager

Responsible for building the conversation
that is sent to the AI provider.
"""

from utils.prompt_loader import build_system_prompt


class ConversationManager:

    async def build(
        self,
        user_id: int,
        message: str,
    ) -> list:

        conversation = []

        # System Prompt
        conversation.append(
            {
                "role": "system",
                "content": build_system_prompt()
            }
        )

        # User Message
        conversation.append(
            {
                "role": "user",
                "content": message
            }
        )

        return conversation


conversation_manager = ConversationManager()
