"""
Gemini Provider
"""


class GeminiProvider:

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        return (
            "Gemini Provider Ready\n\n"
            f"User ID: {user_id}\n"
            f"Messages: {len(conversation)}"
        )
