"""
Prompt Loader

Loads all Nexus prompt files.
"""

from pathlib import Path


PROMPT_DIR = Path("prompts")


def load_prompt(filename: str) -> str:
    """
    Load a prompt file.
    """

    file = PROMPT_DIR / filename

    return file.read_text(
        encoding="utf-8"
    )


def build_system_prompt() -> str:
    """
    Combine all prompt files.
    """

    prompts = [

        load_prompt("base.txt"),

        load_prompt("personality.txt"),

        load_prompt("creator.txt"),

    ]

    return "\n\n".join(prompts)
