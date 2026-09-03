"""
Project Nexus

Facts Manager

Responsible for storing and retrieving what Nexus knows about a person.

The previous version appended blindly: "Name: Rohit", "Lives in: Delhi" and
three copies of "Favorite game: Minecraft" all stacked up, and a correction
("actually I live in Mumbai") became a second permanent fact. Facts now have a
category key, so a new statement about the same subject replaces the old one
instead of contradicting it in the prompt.
"""
from database.database import database, fact_key
from search.query import normalize_query, overlap
from utils.logger import logger
from utils.time_utils import  iso, now_utc

MAX_ACTIVE_FACTS = 60

MAX_PROMPT_FACTS = 18


# ==========================================
# Read
# ==========================================

def get_facts(
    user_id: int,
    *,
    limit: int = MAX_PROMPT_FACTS,
    include_superseded: bool = False,
) -> list[str]:
    """
    Get all facts for a user.
    """
    query = "SELECT fact FROM facts WHERE user_id = ?"

    if not include_superseded:
        query += " AND COALESCE(superseded, 0) = 0"

    query += " ORDER BY COALESCE(updated_at, created_at) DESC, id DESC LIMIT ?"

    rows = database.fetchall(query, (user_id, int(limit)))

    # Oldest-first reads better in a prompt than newest-first.
    return [row["fact"] for row in rows][::-1]


def fact_rows(user_id: int, *, limit: int = 100, include_superseded: bool = False) -> list[dict]:
    """Full rows, for /facts --detailed and the memory audit."""
    query = "SELECT * FROM facts WHERE user_id = ?"

    if not include_superseded:
        query += " AND COALESCE(superseded, 0) = 0"

    query += " ORDER BY id DESC LIMIT ?"

    return [
        dict(row)
        for row in database.fetchall(query, (user_id, int(limit)))
    ]


def relevant_facts(user_id: int, query: str, *, limit: int = MAX_PROMPT_FACTS) -> list[str]:
    """
    Facts most related to the current question first.

    Long-term memory is only useful if it reaches the prompt before the token
    budget runs out, so relevance decides the order.
    """
    rows = fact_rows(user_id, limit=MAX_ACTIVE_FACTS)

    if not rows:
        return []

    scored = sorted(
        rows,
        key=lambda row: (
            overlap(query, row["fact"] or "") * 0.8
            + (0.25 if (row["category"] or "") and (row["category"].lower() in (query or "").lower()) else 0.0),
            row["id"],
        ),
        reverse=True,
    )

    return [row["fact"] for row in scored[:limit]]


def find(user_id: int, term: str) -> list[dict]:
    """Search a user's memory for something they said."""
    needle = f"%{normalize_query(term) or term}%"

    rows = database.fetchall(
        """
        SELECT * FROM facts
         WHERE user_id = ? AND lower(fact) LIKE ?
           AND COALESCE(superseded, 0) = 0
         ORDER BY id DESC
         LIMIT 20
        """,
        (user_id, needle),
    )

    return [dict(row) for row in rows]


# ==========================================
# Write
# ==========================================

def remember_fact(
    user_id: int,
    value: str,
    *,
    category: str | None = None,
    source: str = "conversation",
    confidence: float = 1.0,
) -> dict:
    """
    Store one fact, replacing any older claim about the same subject.

    Returns ``{"action": "added"|"unchanged"|"replaced", ...}`` so callers can
    tell the user what actually happened.
    """
    value = " ".join(str(value or "").split())

    if not value:
        return {"action": "rejected", "reason": "empty fact"}

    fact = value if ":" in value[:40] else f"{(category or 'Note').title()}: {value}"

    key = normalize_query(category) or fact_key(fact)

    existing = database.fetchone(
        """
        SELECT id, fact FROM facts
         WHERE user_id = ? AND key = ? AND COALESCE(superseded, 0) = 0
         ORDER BY id DESC
         LIMIT 1
        """,
        (user_id, key),
    )

    if existing and existing["fact"].strip().lower() == fact.strip().lower():
        return {"action": "unchanged", "fact": fact, "id": existing["id"]}

    replaced = None

    if existing:
        database.execute(
            "UPDATE facts SET superseded = 1 WHERE id = ?",
            (existing["id"],),
        )

        replaced = existing["fact"]

        logger.info(
            "Fact superseded for %s: %r -> %r",
            user_id,
            replaced,
            fact,
        )

    database.execute(
        """
        INSERT INTO facts(
            user_id,
            fact,
            category,
            key,
            confidence,
            source,
            created_at,
            updated_at,
            superseded
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            user_id,
            fact,
            (category or "").title() or None,
            key,
            float(confidence),
            source,
            iso(now_utc()),
            iso(now_utc()),
        ),
    )

    # Keep memory bounded: retire the oldest rows beyond the cap.
    database.execute(
        """
        UPDATE facts SET superseded = 1
         WHERE user_id = ? AND COALESCE(superseded, 0) = 0
           AND id NOT IN (
               SELECT id FROM facts
                WHERE user_id = ? AND COALESCE(superseded, 0) = 0
                ORDER BY id DESC
                LIMIT ?
           )
        """,
        (user_id, user_id, MAX_ACTIVE_FACTS),
    )

    row = database.fetchone(
        "SELECT id FROM facts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )

    logger.info(f"Saved fact for {user_id}")

    return {
        "action": "replaced" if replaced else "added",
        "fact": fact,
        "replaced": replaced,
        "id": row["id"] if row else None,
    }


def add_fact(
    user_id: int,
    fact: str
):
    """
    Save a new fact (backwards-compatible entry point).
    """
    return remember_fact(user_id, fact)


def delete_fact(
    user_id: int,
    fact: str
):
    """
    Delete facts matching a phrase (exact, then by category key, then partial).
    """
    exact = database.fetchall(
        "SELECT id FROM facts WHERE user_id = ? AND fact = ?",
        (user_id, fact),
    )

    if exact:
        database.executemany(
            "DELETE FROM facts WHERE id = ?",
            [(row["id"],) for row in exact],
        )

        return len(exact)

    key = fact_key(fact)

    by_key = database.fetchall(
        "SELECT id FROM facts WHERE user_id = ? AND key = ?",
        (user_id, key),
    )

    if by_key:
        database.executemany(
            "DELETE FROM facts WHERE id = ?",
            [(row["id"],) for row in by_key],
        )

        return len(by_key)

    removed = database.execute_count(
        "DELETE FROM facts WHERE user_id = ? AND fact LIKE ?",
        (user_id, f"%{normalize_query(fact) or fact}%"),
    )

    return removed


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


def stats(user_id: int) -> dict:
    row = database.fetchone(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN COALESCE(superseded, 0) = 0 THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN COALESCE(superseded, 0) = 1 THEN 1 ELSE 0 END) AS superseded,
            MAX(COALESCE(updated_at, created_at)) AS last_update
        FROM facts
        WHERE user_id = ?
        """,
        (user_id,),
    )

    return dict(row or {})
