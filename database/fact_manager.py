"""
Project Nexus

Facts Manager

Responsible for storing and retrieving
user facts.
"""

from database.database import database
from utils.logger import logger


def get_facts(user_id: int) -> list[str]:
    """
    Get all facts for a user.
    """

    rows = database.fetchall(
        """
        SELECT fact
        FROM facts
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (user_id,)
    )

    return [
        row["fact"]
        for row in rows
    ]


def add_fact(
    user_id: int,
    fact: str
):
    """
    Save a new fact.
    """

    # Prevent duplicates
    existing = database.fetchone(
        """
        SELECT id
        FROM facts
        WHERE user_id = ?
        AND fact = ?
        """,
        (
            user_id,
            fact
        )
    )

    if existing:
        return

    database.execute(
        """
        INSERT INTO facts(
            user_id,
            fact
        )
        VALUES (?, ?)
        """,
        (
            user_id,
            fact
        )
    )

    logger.info(
        f"Saved fact for {user_id}"
    )


def delete_fact(
    user_id: int,
    fact: str
):
    """
    Delete a specific fact.
    """

    database.execute(
        """
        DELETE FROM facts
        WHERE user_id = ?
        AND fact = ?
        """,
        (
            user_id,
            fact
        )
    )


def clear_facts(user_id: int):
    """
    Remove all facts for a user.
    """

    database.execute(
        """
        DELETE FROM facts
        WHERE user_id = ?
        """,
        (user_id,)
    )

    logger.info(
        f"Cleared facts for {user_id}"
    )
