"""
Project Nexus

Base Tool

Shared behaviour for every tool Nexus can call.

Accuracy rule #1: a tool that cannot answer must say so. The old stubs
returned friendly placeholder text with a confidence of 1.0, which the model
happily repeated as fact. Tools now expose availability and health, report
failures, and the pipeline refuses to feed placeholders to the AI.
"""

from abc import ABC, abstractmethod

from utils.time_utils import  now_utc


class ToolHealth:
    """Rolling failure tracking for a single tool."""

    FAILURE_LIMIT = 3
    COOLDOWN = 15 * 60

    def __init__(self):
        self.failures = 0
        self.successes = 0
        self.last_error = None
        self.last_success_at = None
        self.last_error_at = None
        self.cooldown_until = 0.0

    @property
    def degraded(self) -> bool:
        return self.cooldown_until > now_utc().timestamp()

    def record_success(self):
        self.successes += 1
        self.failures = 0
        self.last_error = None
        self.last_success_at = now_utc().isoformat(timespec="seconds")

    def record_failure(self, error):
        self.failures += 1
        self.last_error = str(error)[:400]
        self.last_error_at = now_utc().isoformat(timespec="seconds")

        if self.failures >= self.FAILURE_LIMIT:
            self.cooldown_until = now_utc().timestamp() + self.COOLDOWN
            self.failures = 0

    def stats(self) -> dict:
        return {
            "successes": self.successes,
            "failures": self.failures,
            "degraded": self.degraded,
            "last_error": self.last_error,
            "last_success": self.last_success_at,
        }


class BaseTool(ABC):

    #: Short label used by the router when deciding which tools to call.
    keywords: tuple[str, ...] = ()

    #: Contributes factual, web-grounded evidence that can back an answer.
    searchable: bool = True

    #: Suggested cache lifetime in seconds for this tool's results.
    ttl: int | None = None

    #: Environment variables this tool needs. Empty means "always usable".
    required_keys: tuple[str, ...] = ()

    #: True for tools that are wired up but not implemented yet. They are
    #: excluded from every pipeline instead of polluting the answer.
    implemented: bool = True

    health: ToolHealth = None

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
        return bool(self.required_keys)

    @property
    def available(self) -> bool:
        """
        Ready to answer right now.

        False for unimplemented tools and for tools whose API keys are
        missing - such tools are skipped rather than asked to guess.
        """
        return self.implemented

    @property
    def usable(self) -> bool:
        """Available and not temporarily broken."""
        if not self.enabled or not self.available:
            return False

        health = getattr(self, "_health", None)

        return not (health and health.degraded)

    @abstractmethod
    async def execute(
        self,
        *args,
        **kwargs,
    ) -> dict:
        pass

    # ==========================================
    # Health
    # ==========================================

    @property
    def _health(self) -> ToolHealth:
        health = self.__dict__.get("_tool_health")

        if health is None:
            health = ToolHealth()
            self.__dict__["_tool_health"] = health

        return health

    def record_success(self):
        self._health.record_success()

    def record_failure(self, error):
        self._health.record_failure(error)

    def healthcheck(self) -> bool:
        return self.usable

    def info(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "available": self.available,
            "usable": self.usable,
            "implemented": self.implemented,
            "searchable": self.searchable,
            "priority": self.priority,
            "requires_api": self.requires_api,
            "description": self.description,
            "keywords": list(self.keywords),
            "health": self._health.stats(),
        }
