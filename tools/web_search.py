"""
Project Nexus

Web Search Tool
"""

from tools.base import BaseTool

from utils.logger import logger


class WebSearchTool(BaseTool):

    @property
    def name(self):

        return "web_search"

    async def execute(
        self,
        query: str,
    ):

        logger.info(
            f"Web Search: {query}"
        )

        return {
            "success": False,
            "content": None
        }


web_search = WebSearchTool()
