"""
Project Nexus

Prompt Loader
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from utils.logger import logger


PROMPT_DIR = (
    Path(__file__).resolve().parent.parent
    / "prompts"
)

INDIA_TIMEZONE = timezone(
    timedelta(hours=5, minutes=30),
    name="IST",
)


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


def build_runtime_context() -> str:
    now_utc = datetime.now(timezone.utc)
    now_india = now_utc.astimezone(
        INDIA_TIMEZONE
    )

    return (
        "Verified runtime context:\n"
        f"- Current UTC date and time: "
        f"{now_utc.strftime('%A, %d %B %Y, %H:%M UTC')}\n"
        f"- Current India date and time: "
        f"{now_india.strftime('%A, %d %B %Y, %I:%M %p IST')}\n\n"
        "Accuracy requirements:\n"
        "- Treat the runtime date and time above as authoritative.\n"
        "- Never claim you cannot access the current date or time.\n"
        "- Use supplied search context for current information.\n"
        "- Never invent live facts, sources, links, or quotations.\n"
        "- If current information was not supplied or verified, "
        "say that clearly instead of guessing."
    )


def build_system_prompt() -> str:
    prompts = [
        load_prompt("base.txt"),
        load_prompt("personality.txt"),
        load_prompt("creator.txt"),
        build_runtime_context(),
    ]

    return "\n\n".join(
        prompt
        for prompt in prompts
        if prompt
    )