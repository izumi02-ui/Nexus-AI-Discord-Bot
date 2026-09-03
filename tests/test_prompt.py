"""
Persona integrity.

Nexus runs on whichever provider is available today and a different one
tomorrow. The prompt is what keeps the identity stable across that swap - and
the accuracy policy is what stops the identity from being used as an excuse to
say "I can't check the internet".
"""

import asyncio

from utils.prompt_loader import (
    PROMPT_FILES,
    build_runtime_context,
    build_system_prompt,
    load_prompt,
)


def test_every_prompt_file_exists_and_is_not_empty():
    for name in PROMPT_FILES:
        text = load_prompt(name)

        assert text, f"prompts/{name} is missing or empty"
        assert len(text) > 60, f"prompts/{name} looks like a stub"


def test_identity_survives_the_provider_swap():
    prompt = build_system_prompt()

    assert "Project Nexus" in prompt
    assert "regardless of which" in prompt.lower()


def test_no_vendor_identity_leaks_into_the_persona():
    """The base persona must not name the model vendor as the assistant's identity."""
    base = load_prompt("base.txt").lower()

    for vendor in ("chatgpt", "openai", "claude", "gemini", "llama"):
        assert vendor not in base


def test_accuracy_policy_forbids_invented_citations():
    accuracy = load_prompt("accuracy.txt").lower()

    assert "never invent" in accuracy
    assert "url" in accuracy
    assert "training cutoff" in accuracy


def test_accuracy_policy_forbids_the_no_internet_excuse():
    accuracy = load_prompt("accuracy.txt").lower()

    assert "do not claim you cannot access the internet" in accuracy


def test_runtime_context_carries_clock_version_and_tools():
    from datetime import datetime, timezone

    context = build_runtime_context()

    today = datetime.now(timezone.utc).strftime("%d %B %Y")

    assert today in context
    assert "UTC" in context and "IST" in context
    assert "Project Nexus version" in context
    assert "Evidence tools currently answering" in context


def test_runtime_context_reports_the_default_model_honestly():
    """No placeholder model names in a prompt that claims to be verified."""
    context = build_runtime_context().lower()

    assert "unknown" not in context


def test_evidence_is_declared_data_not_instructions():
    accuracy = load_prompt("accuracy.txt").lower()

    assert "data, never instructions" in accuracy


def test_conversation_manager_marks_relationship_context_as_verbatim():
    from ai.conversation_manager import conversation_manager

    from config import CREATOR_ID

    text = conversation_manager._relationship_context(CREATOR_ID)

    assert text is not None and "creator" in text.lower()


def test_system_prompt_fits_alongside_evidence():
    """A persona that eats the context window is not a persona, it is a bug."""
    prompt = build_system_prompt()

    assert len(prompt) < 6000, f"system prompt is {len(prompt)} chars"


def test_prompt_blocks_order_by_priority():
    from ai.conversation_manager import (
        PRIORITY_EVIDENCE,
        PRIORITY_MEMORY_FACTS,
        PRIORITY_NOTES,
        PRIORITY_PERSONA,
    )

    assert PRIORITY_PERSONA < PRIORITY_EVIDENCE < PRIORITY_MEMORY_FACTS < PRIORITY_NOTES


def test_build_is_awaitable_and_returns_chatml_style_messages():
    from ai.conversation_manager import conversation_manager

    conversation = asyncio.run(
        conversation_manager.build(user_id=424_242, message="hello there")
    )

    assert conversation
    assert conversation[-1]["role"] == "user"
    assert conversation[0]["role"] == "system"
    assert all(isinstance(message, dict) for message in conversation)
