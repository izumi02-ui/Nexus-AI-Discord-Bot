"""
Project Nexus

AI Engine

The heart of Nexus.
"""

from ai.memory_manager import MemoryManager


class AIEngine:

    def __init__(self):

        self.memory = MemoryManager()

    async def ask(
        self,
        user_id: int,
        message: str,
    ) -> str:

        return await self.memory.process(
            user_id=user_id,
            message=message
        )


engine = AIEngine()
