"""
Project Nexus

AI Tool Calling
"""

from tools.manager import tool_manager

from utils.logger import logger


class ToolCalling:

    async def execute(
        self,
        tool: str,
        query: str,
    ):

        logger.info(
            f"Executing tool: {tool}"
        )

        return await tool_manager.execute(

            tool,

            query,

        )


tool_calling = ToolCalling()
