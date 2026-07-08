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
            "Tool Manager Ready."
        )

    async def execute(
        self,
        tool: str,
        query: str,
    ):

        tool = self.tools.get(tool)

        if tool is None:

            raise ValueError(
                f"Unknown tool: {tool}"
            )

        return await tool.execute(
            query
        )

    @property
    def available(self):

        return list(
            self.tools.keys()
        )


tool_manager = ToolManager()
