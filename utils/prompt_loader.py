"""
Project Nexus

Prompt Loader

Loads Nexus prompt files.
"""

from pathlib import Path

from utils.logger import logger

PROMPT_DIR = Path("prompts")


def load_prompt(filename: str) -> str:
    """
    Load a single prompt file.
    """

    file = PROMPT_DIR / filename

    if not file.exists():

        logger.warning(
            f"Prompt file not found: {filename}"
        )

        return ""

    return file.read_text(
        encoding="utf-8"
    )


def build_system_prompt() -> str:
    """
    Build the complete system prompt.
    """

    prompts = [
        load_prompt("base.txt"),
        load_prompt("personality.txt"),
        load_prompt("creator.txt"),
    ]

    return "\n\n".join(
        prompt
        for prompt in prompts
        if prompt
    )
