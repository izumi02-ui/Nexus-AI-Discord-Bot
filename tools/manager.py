"""
Project Nexus

Tool Manager
"""

from tools.google_search import google_search

from utils.logger import logger


class ToolManager:

    def __init__(self):

        self.tools = {

            google_search.name: google_search,

        }

        logger.info(
            "Tool Manager Ready."
        )

    async def execute(
        self,
        tool: str,
        query: str,
    ):

        tool_instance = self.tools.get(
            tool
        )

        if tool_instance is None:

            raise ValueError(
                f"Unknown tool: {tool}"
            )

        return await tool_instance.execute(
            query
        )

    @property
    def available(self):

        return list(
            self.tools.keys()
        )


tool_manager = ToolManager()
