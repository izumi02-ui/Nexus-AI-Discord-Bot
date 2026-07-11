"""
Project Nexus

Tool Registry
"""

from tools.manager import tool_manager


class ToolRegistry:

    def all(self):

        return tool_manager.available

    def exists(
        self,
        tool: str,
    ):

        return tool in tool_manager.available

    def get(
        self,
        tool: str,
    ):

        return tool_manager.get(tool)


tool_registry = ToolRegistry()
