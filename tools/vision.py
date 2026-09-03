"""
Project Nexus

Vision Tool (not implemented)

Image understanding is provided by the AI providers themselves (Gemini,
OpenAI, OpenRouter vision models); a separate fake "vision" tool only ever
invented captions, so it is explicitly unavailable until implemented.
"""

from typing import List

from tools.base import BaseTool


class VisionTool(BaseTool):

    keywords = ("image", "picture", "photo", "what is in this")

    implemented = False
    searchable = False

    @property
    def name(self) -> str:
        return "vision"

    @property
    def description(self) -> str:
        return "Image understanding (use a vision-capable provider for now)"

    async def execute(self, query: str) -> List:
        raise NotImplementedError(
            "Vision is handled by the provider's own capabilities "
            "(provider.supports('vision')); this standalone tool is a stub."
        )


vision = VisionTool()
