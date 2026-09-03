"""
Project Nexus

Prompt Loader

Assembles the system prompt from the files in /prompts plus a runtime block
that is regenerated on every request.

The runtime block is what keeps the persona honest about the present: the
clock, the version that is actually running, which provider and model are
answering, how many evidence tools are alive right now, and when the self
updater last refreshed things. Nothing in it is remembered from training.
"""

from pathlib import Path

from utils.logger import logger
from utils.time_utils import INDIA_TIMEZONE, humanize_age, now_utc

PROMPT_DIR = (
    Path(__file__).resolve().parent.parent
    / "prompts"
)

#: Loaded in this order; persona first so it survives prompt truncation.
PROMPT_FILES = [
    "base.txt",
    "personality.txt",
    "creator.txt",
    "accuracy.txt",
]


def load_prompt(filename: str) -> str:
    file = PROMPT_DIR / filename

    if not file.exists():
        logger.warning(
            "Prompt file not found: %s",
            filename,
        )

        return ""

    return file.read_text(
        encoding="utf-8"
    ).strip()


def _cache_ttl_note() -> str:
    from search.freshness import INSTANT, SHORT

    return (
        f"- Questions about prices, weather, scores or anything 'right now' are "
        f"answered only from evidence at most a few minutes old (limit "
        f"{INSTANT // 60} minutes); news and 'current role holder' questions "
        f"allow about {SHORT // 3600} hours."
    )


def build_runtime_context() -> str:
    """Facts about this exact process, right now."""
    from config import VERSION

    now = now_utc()
    now_india = now.astimezone(INDIA_TIMEZONE)

    lines = [
        "Verified runtime context (regenerated for every request):",
        f"- Current UTC date and time: {now.strftime('%A, %d %B %Y, %H:%M UTC')}",
        f"- Current India date and time: {now_india.strftime('%A, %d %B %Y, %I:%M %p IST')}",
        f"- Project Nexus version: {VERSION}",
    ]

    provider_line = None

    try:
        from ai.provider_manager import provider_manager

        provider_line = (
            f"- Running on provider {provider_manager.name}, model "
            f"{provider_manager.model}."
        )
    except Exception as error:  # noqa: BLE001 - prompt must build regardless
        logger.debug("Provider info unavailable for prompt: %s", error)

    if provider_line:
        lines.append(provider_line)

    try:
        from tools.manager import tool_manager

        usable = [tool.name for tool in tool_manager.usable_tools()]

        lines.append(
            f"- Evidence tools currently answering ({len(usable)}): "
            + (", ".join(usable) if usable else "none configured")
        )

        unavailable = [
            name
            for name in tool_manager.tools
            if not tool_manager.tools[name].usable
        ]

        if unavailable:
            lines.append(
                "- Unavailable tools (skip them, do not apologize for them): "
                + ", ".join(sorted(unavailable)[:6])
            )
    except Exception as error:  # noqa: BLE001
        logger.debug("Tool inventory unavailable: %s", error)

    try:
        from core.updater import updater

        state = updater.state

        if state.get("last_cycle_at"):
            lines.append(
                "- Nexus' verified notes were last re-checked "
                f"{humanize_age(state['last_cycle_at'])}."
            )
        else:
            lines.append(
                "- Nexus' self-check has not run yet in this session."
            )
    except Exception:  # noqa: BLE001
        pass

    lines += [
        "",
        "Accuracy requirements:",
        "- Treat the runtime date and time above as authoritative.",
        "- Never claim you cannot access the current date or time.",
        "- Use supplied evidence for current information; never substitute memory.",
        "- Never invent live facts, sources, links, or quotations.",
        "- If current information was not supplied or verified, say that plainly "
        "instead of guessing.",
        _cache_ttl_note(),
    ]

    return "\n".join(line for line in lines if line is not None)


def build_system_prompt() -> str:
    prompts = [
        load_prompt(filename)
        for filename in PROMPT_FILES
    ]

    prompts.append(build_runtime_context())

    return "\n\n".join(
        prompt
        for prompt in prompts
        if prompt
    )
