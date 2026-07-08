"""
Project Nexus

Memory Manager

Stores recent conversations for each user.
"""

from database.database import database
from utils.settings import settings
from utils.logger import logger


def add_message(
    user_id: int,
    role: str,
    content: str
):
    """
    Save a conversation message.
    """

    database.execute(
        """
        INSERT INTO memories(
            user_id,
            role,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            role,
            content
        )
    )


def get_memory(user_id: int):

    rows = database.fetchall(
        """
        SELECT role, content
        FROM memories
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            user_id,
            settings.memory_limit
        )
    )

    rows.reverse()

    return [
        {
            "role": row["role"],
            "content": row["content"]
        }
        for row in rows
    ]


def clear_memory(user_id: int):

    database.execute(
        """
        DELETE FROM memories
        WHERE user_id = ?
        """,
        (user_id,)
    )

    logger.info(
        f"Cleared memory for {user_id}"
    )
