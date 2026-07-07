"""
Project Nexus

Gemini Provider
"""

from ai.providers.base import BaseProvider


class GeminiProvider(BaseProvider):

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        return (
            "Gemini Provider Ready\n"
            f"User: {user_id}\n"
            f"Messages: {len(conversation)}"
        )
