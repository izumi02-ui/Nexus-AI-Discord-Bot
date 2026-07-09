"""
Project Nexus

Web Search Tool
"""

from ai.provider_manager import provider_manager

from tools.base import BaseTool
from tools.result import ToolResult

from utils.logger import logger


class WebSearchTool(BaseTool):

    @property
    def name(self):

        return "web_search"

    async def execute(
        self,
        query: str,
    ) -> ToolResult:

        logger.info(
            f"Searching Web: {query}"
        )

        provider = provider_manager.provider

        if not provider.supports(
            "web_search"
        ):

            return ToolResult(
                success=False,
                error=f"{provider.name} does not support web search."
            )

        try:

            result = await provider.use_tool(
                "web_search",
                query
            )

            return ToolResult(
                success=True,
                content=result
            )

        except Exception as error:

            logger.exception(
                "Web Search Failed"
            )

            return ToolResult(
                success=False,
                error=str(error)
            )


web_search = WebSearchTool()
