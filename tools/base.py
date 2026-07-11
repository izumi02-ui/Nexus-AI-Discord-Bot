"""
Project Nexus

Base Tool
"""

from abc import ABC, abstractmethod


class BaseTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def enabled(self) -> bool:
        return True

    @property
    def priority(self) -> int:
        return 100

    @property
    def description(self) -> str:
        return self.name

    @property
    def requires_api(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    async def execute(
        self,
        *args,
        **kwargs,
    ) -> dict:
        pass

    async def healthcheck(
        self,
    ) -> bool:

        return self.available

    def info(
        self,
    ) -> dict:

        return {

            "name": self.name,

            "enabled": self.enabled,

            "available": self.available,

            "priority": self.priority,

            "requires_api": self.requires_api,

            "description": self.description,

        }
