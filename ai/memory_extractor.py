"""
Project Nexus

Memory Extractor

Extracts long-term facts from conversations.
"""

from utils.logger import logger


class MemoryExtractor:

    def extract(
        self,
        user_id: int,
        message: str,
        response: str,
    ):
        """
        Analyze a conversation and decide
        what should become long-term memory.

        (Coming in Alpha.2)
        """

        logger.info(
            f"Memory extraction skipped for {user_id}"
        )


memory_extractor = MemoryExtractor()
