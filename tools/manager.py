"""
Project Nexus

Tool Manager
"""

from tools.web_search import web_search

from utils.logger import logger


class ToolManager:

    def __init__(self):

        self.tools = {

            web_search.name: web_search,

        }

        logger.info(
            f"Loaded {len(self.tools)} tools."
        )

    async def execute(
        self,
        tool_name: str,
        query: str,
    ):

        tool = self.tools.get(
            tool_name
        )

        if tool is None:

            raise ValueError(
                f"Unknown tool: {tool_name}"
            )

        logger.info(
            f"Executing tool: {tool_name}"
        )

        return await tool.execute(
            query
        )

    def register(
        self,
        tool,
    ):

        self.tools[tool.name] = tool

        logger.info(
            f"Registered tool: {tool.name}"
        )

    @property
    def available(self):

        return list(
            self.tools.keys()
        )


tool_manager = ToolManager()
