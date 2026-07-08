"""
Project Nexus

Conversation Message Helpers
"""


def system(content: str) -> dict:

    return {
        "role": "system",
        "content": content
    }


def user(content: str) -> dict:

    return {
        "role": "user",
        "content": content
    }


def assistant(content: str) -> dict:

    return {
        "role": "assistant",
        "content": content
    }
