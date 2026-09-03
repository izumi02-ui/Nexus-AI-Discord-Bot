"""
Project Nexus

Tool Manager

Registers every tool, keeps a record of how each one is behaving, and decides
which tools are worth calling for a given question.

Two policies the accuracy pipeline depends on:

  * a tool that is not configured is skipped, never queried;
  * a tool that keeps failing is put in a cooldown so a broken integration
    cannot drag every answer down or spam the same API.
"""

import time
from typing import Iterable

from utils.logger import logger
from utils.time_utils import parse_datetime

# Tools that contribute real-world evidence (as opposed to local computation).
SEARCH_TIER = {
    "brave": 100,
    "google": 99,
    "web_search": 98,
    "wikipedia": 95,
    "news": 94,
    "github": 92,
    "stackoverflow": 91,
    "arxiv": 90,
    "weather": 99,
    "currency": 99,
    "time": 99,
    "calculator": 99,
    "maps": 88,
    "steam": 87,
    "spotify": 86,
    "reddit": 80,
    "duckduckgo": 78,
    "web_scraper": 76,
    "translator": 74,
}


class ToolManager:

    def __init__(self):

        self.tools = {}

        self.results = {}

        self.started_at = time.time()

    # =====================================

    def register(
        self,
        tool,
    ):

        if tool.name in self.tools:

            logger.warning(
                f"Tool '{tool.name}' already registered."
            )

            return

        self.tools[tool.name] = tool

        status = "ready" if tool.available else "unavailable (not configured)"

        logger.info(f"Loaded Tool: {tool.name} - {status}")

    # =====================================

    def register_many(
        self,
        *tools,
    ):

        for tool in tools:

            self.register(tool)

        logger.info(
            f"{len(self.available_tools())} usable tools "
            f"({len(self.tools)} registered)."
        )

    # =====================================

    async def execute(
        self,
        tool_name: str,
        *args,
        **kwargs,
    ):

        tool = self.tools.get(
            tool_name
        )

        if tool is None:

            return {

                "success": False,

                "error": f"Unknown tool: {tool_name}",

            }

        try:

            result = await tool.execute(
                *args,
                **kwargs,
            )

            tool.record_success()

            return result

        except Exception as error:

            tool.record_failure(error)

            logger.warning(
                f"{tool_name} failed: {error}"
            )

            return {

                "success": False,

                "error": str(error),

            }

    # =====================================

    @property
    def available(self) -> list:
        """Names of every tool that can answer right now (API + /health)."""
        return [tool.name for tool in self.usable_tools()]

    def get(
        self,
        name: str,
    ):

        return self.tools.get(name)

    # =====================================
    # Availability
    # =====================================

    def usable_tools(self) -> list:
        """Registered tools that are configured and not currently broken."""
        usable = []

        for tool in self.tools.values():
            try:
                if tool.usable:
                    usable.append(tool)
            except Exception as error:  # pragma: no cover - defensive
                logger.warning("Tool %s health check failed: %s", tool.name, error)

        return usable

    def search_tools(self) -> list:
        """Usable tools that are allowed to answer factual questions."""
        tools = [
            tool
            for tool in self.usable_tools()
            if getattr(tool, "searchable", True)
        ]

        return sorted(
            tools,
            key=lambda tool: (
                -(SEARCH_TIER.get(tool.name, tool.priority)),
                tool.name,
            ),
        )

    def select(self, names: Iterable[str] | None = None) -> list:
        """
        Resolve a requested tool list down to tools that can actually run.

        Unknown or unavailable names are dropped and logged - that is what
        stops placeholder output from ever reaching the model.
        """
        if names is None:
            return self.search_tools()

        selected = []
        dropped = []

        for name in names:
            tool = self.tools.get(name)

            if tool is None:
                dropped.append(f"{name} (not registered)")
                continue

            if not tool.usable:
                reason = "disabled"

                if not tool.available:
                    reason = (
                        "not implemented"
                        if not tool.implemented
                        else "missing API key"
                    )
                elif tool._health.degraded:
                    reason = "in cooldown"

                dropped.append(f"{name} ({reason})")
                continue

            if not getattr(tool, "searchable", True) and name not in SEARCH_TIER:
                dropped.append(f"{name} (not a search source)")
                continue

            selected.append(tool)

        if dropped:
            logger.info("Skipped tools: %s", ", ".join(dropped))

        return selected

    # =====================================
    # Health reporting
    # =====================================

    def report(self) -> dict:
        rows = []

        for name in sorted(self.tools):
            info = self.tools[name].info()

            info["suggested_tier"] = SEARCH_TIER.get(name, 50)
            info["recent_results"] = len(self.results.get(name, []))

            rows.append(info)

        usable = [row["name"] for row in rows if row["usable"]]
        idle = [row["name"] for row in rows if not row["usable"]]

        return {
            "registered": len(rows),
            "usable": usable,
            "unavailable": idle,
            "uptime_seconds": int(time.time() - self.started_at),
            "tools": rows,
        }

    def record_result(self, tool_name: str, count: int):
        """Remember what each tool recently returned, for /health and the updater."""
        history = self.results.setdefault(tool_name, [])

        history.append(
            {
                "at": parse_datetime(time.time()).isoformat(timespec="seconds"),
                "results": count,
            }
        )

        del history[:-10]


tool_manager = ToolManager()


# =====================================
# Register Tools
# =====================================

import importlib

#: (module, attribute) for every tool. Each import is guarded: a tool whose
#: optional dependency is missing is reported as failed to load and skipped,
#: instead of taking the whole bot down at startup.
TOOL_MODULES = [
    ("tools.brave", "brave"),
    ("tools.google_search", "google_search"),
    ("tools.web_search", "web_search"),
    ("tools.wikipedia", "wikipedia"),
    ("tools.news", "news"),
    ("tools.arxiv", "arxiv"),
    ("tools.stackoverflow", "stackoverflow"),
    ("tools.github", "github"),
    ("tools.weather", "weather"),
    ("tools.currency", "currency"),
    ("tools.time", "time_tool"),
    ("tools.maps", "maps"),
    ("tools.steam", "steam"),
    ("tools.spotify", "spotify"),
    ("tools.youtube", "youtube"),
    ("tools.reddit", "reddit"),
    ("tools.duckduckgo", "duckduckgo"),
    ("tools.web_scraper", "web_scraper"),
    ("tools.translator", "translator"),
    ("tools.calculator", "calculator"),
    ("tools.file_reader", "file_reader"),
    ("tools.ocr", "ocr"),
    ("tools.vision", "vision"),
]

_load_failures = {}

for _module_name, _attribute in TOOL_MODULES:
    try:
        tool_manager.register(
            getattr(importlib.import_module(_module_name), _attribute)
        )
    except Exception as _error:  # noqa: BLE001 - startup must survive this
        _load_failures[_module_name] = str(_error)
        logger.warning(
            "Tool %s could not load: %s",
            _module_name,
            _error,
        )

if _load_failures:
    logger.warning(
        "%s tool(s) failed to load: %s",
        len(_load_failures),
        ", ".join(sorted(_load_failures)),
    )
