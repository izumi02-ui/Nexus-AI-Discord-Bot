"""
Project Nexus

Knowledge

Nexus' verified, self-updating store of claims about the world.

This is the "update itself" half of the project. A row here is not a hunch
from a language model: every entry carries where it came from, when it was
last checked, and a deadline after which it is not allowed to be quoted as
current. The background updater walks those deadlines, re-runs the search
tools, stores the new value and records what changed.

    user memory (facts)  ->  what a person told Nexus
    knowledge             ->  what Nexus verified, with a shelf life
"""

from datetime import timedelta

from database.database import database
from search.query import normalize_query, overlap, topic_of
from utils.logger import logger
from utils.time_utils import HOUR, iso, now_utc

FRESH = "active"
STALE = "stale"
DISPUTED = "disputed"
RETIRED = "retired"

_RANKING = """
    ORDER BY
        CASE WHEN stale_after IS NULL OR stale_after > ?
             THEN 0 ELSE 1 END,
        confidence DESC,
        COALESCE(verified_at, created_at) DESC
"""


# ==========================================
# Write
# ==========================================

def remember(
    value: str,
    *,
    topic: str | None = None,
    claim: str = "",
    source: str | None = None,
    url: str | None = None,
    tool: str | None = None,
    confidence: float = 0.8,
    ttl_seconds: int | None = None,
    user_id: int | None = None,
    notes: str | None = None,
    reason: str = "verified",
) -> int | None:
    """
    Store or refresh a verified claim.

    Returns the row id, or None when the value was identical and nothing
    changed (the timestamp is still pushed forward in that case).
    """
    value = " ".join(str(value or "").split())

    if not value:
        logger.warning("knowledge.remember: refused an empty value")

        return None

    topic = normalize_query(topic or topic_of(value)) or "general"
    claim = " ".join(str(claim or "").split())[:180]

    existing = database.fetchone(
        "SELECT id, value, confidence FROM knowledge "
        "WHERE topic = ? AND claim = ?",
        (topic, claim),
    )

    now = iso(now_utc())
    ttl = int(ttl_seconds) if ttl_seconds else None
    stale_after = iso(now_utc() + timedelta(seconds=ttl)) if ttl else None

    if existing:
        changed = (existing["value"] or "").strip() != value

        if changed:
            database.execute(
                """
                INSERT INTO knowledge_history(
                    topic, claim, old_value, new_value, reason, source, changed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (topic, claim, existing["value"], value, reason, source, now),
            )

            logger.info(
                "Knowledge updated (%s%s): %s",
                topic,
                f" [{claim}]" if claim else "",
                value[:120],
            )

        database.execute(
            """
            UPDATE knowledge
               SET value = ?,
                   source = COALESCE(?, source),
                   url = COALESCE(?, url),
                   tool = COALESCE(?, tool),
                   confidence = MAX(confidence, ?),
                   verified_at = ?,
                   stale_after = ?,
                   ttl_seconds = ?,
                   status = ?,
                   notes = COALESCE(?, notes),
                   user_id = COALESCE(?, user_id)
             WHERE id = ?
            """,
            (
                value,
                source,
                url,
                tool,
                float(confidence),
                now,
                stale_after,
                ttl,
                FRESH,
                notes,
                user_id,
                existing["id"],
            ),
        )

        return existing["id"]

    database.execute(
        """
        INSERT INTO knowledge(
            topic, claim, value, source, url, tool, confidence,
            verified_at, stale_after, ttl_seconds, user_id, status, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            topic,
            claim,
            value,
            source,
            url,
            tool,
            float(confidence),
            now,
            stale_after,
            ttl,
            user_id,
            FRESH,
            notes,
            now,
        ),
    )

    row = database.fetchone(
        "SELECT id FROM knowledge WHERE topic = ? AND claim = ?",
        (topic, claim),
    )

    logger.info(
        "Knowledge learned (%s): %s",
        topic,
        value[:120],
    )

    return row["id"] if row else None


def remember_from_results(query: str, results, *, user_id: int | None = None) -> int | None:
    """
    Distill a verified search result into the knowledge base.

    Only called when the evidence was strong enough to state as fact - the
    caller (engine/updater) is responsible for that judgement.
    """
    best = results[0] if isinstance(results, (list, tuple)) and results else None

    if best is None:
        return None

    content = " ".join((best.content or "").split())

    return remember(
        content[:1200],
        topic=topic_of(query),
        claim=(best.title or "")[:180],
        source=best.source,
        url=best.url,
        tool=best.tool,
        confidence=min(0.9, float(best.score_of() or 0.7)),
        ttl_seconds=int(best.metadata.get("tool_ttl") or 6 * HOUR),
        user_id=user_id,
        reason="answer verified",
    )


def mark_stale(row_id: int, note: str | None = None):
    database.execute(
        "UPDATE knowledge SET status = ?, notes = COALESCE(?, notes) WHERE id = ?",
        (STALE, note, row_id),
    )


def mark_disputed(row_id: int, note: str):
    """
    Sources contradicted each other: park the row instead of trusting it.

    A disputed entry is never injected into a prompt - it is evidence that
    Nexus has to say "I could not confirm this".
    """
    database.execute(
        "UPDATE knowledge SET status = ?, notes = ? WHERE id = ?",
        (DISPUTED, note[:500], row_id),
    )


def retire(row_id: int, reason: str = "retired"):
    row = database.fetchone(
        "SELECT topic, claim, value FROM knowledge WHERE id = ?",
        (row_id,),
    )

    if not row:
        return False

    database.execute(
        "UPDATE knowledge SET status = ? WHERE id = ?",
        (RETIRED, row_id),
    )

    database.execute(
        """
        INSERT INTO knowledge_history(topic, claim, old_value, new_value, reason)
        VALUES (?, ?, ?, '', ?)
        """,
        (row["topic"], row["claim"], row["value"], reason),
    )

    return True


def bump_confidence(row_id: int, delta: float = 0.05, *, cap: float = 0.98):
    database.execute(
        "UPDATE knowledge SET confidence = MIN(?, confidence + ?) WHERE id = ?",
        (cap, delta, row_id),
    )


def decay_confidence(row_id: int, delta: float = 0.15, floor: float = 0.2):
    """A recalled fact that the current evidence contradicts."""
    database.execute(
        "UPDATE knowledge SET confidence = MAX(?, confidence - ?), status = ? "
        "WHERE id = ?",
        (floor, delta, STALE, row_id),
    )


def prune(min_confidence: float = 0.35, keep: int = 2000) -> dict:
    """
    Drop what is no longer worth keeping.

    Retired rows, low-confidence rows and rows over the cap (oldest first) are
    removed; the history table is untouched so corrections stay auditable.
    """
    removed_retired = database.execute_count(
        "DELETE FROM knowledge WHERE status = ?", (RETIRED,)
    )

    removed_weak = database.execute_count(
        "DELETE FROM knowledge WHERE confidence < ?", (float(min_confidence),)
    )

    excess = database.execute_count(
        """
        DELETE FROM knowledge
         WHERE id NOT IN (
             SELECT id FROM knowledge
              ORDER BY COALESCE(verified_at, created_at) DESC
              LIMIT ?
         )
        """,
        (int(keep),),
    )

    counts = {
        "retired": removed_retired or 0,
        "low_confidence": removed_weak or 0,
        "excess": excess or 0,
    }

    if any(counts.values()):
        logger.info("Knowledge pruned: %s", counts)

    return counts


# ==========================================
# Read
# ==========================================

def get(row_id: int) -> dict | None:
    row = database.fetchone("SELECT * FROM knowledge WHERE id = ?", (row_id,))

    return dict(row) if row else None


def find(topic: str, claim: str = "") -> dict | None:
    row = database.fetchone(
        "SELECT * FROM knowledge WHERE topic = ? AND claim = ?",
        (normalize_query(topic), claim),
    )

    return dict(row) if row else None


def recall(
    query: str,
    *,
    limit: int = 4,
    min_confidence: float = 0.5,
    require_fresh: bool = True,
) -> list[dict]:
    """
    Anything Nexus already verified that helps answer this question?

    Matching is topic equality plus word overlap, and a row whose shelf life
    has run out is only returned when the caller explicitly allows stale
    background (require_fresh=False).
    """
    topic = topic_of(query)

    now = iso(now_utc())

    rows = database.fetchall(
        f"""
        SELECT * FROM knowledge
         WHERE status IN ('{FRESH}', '{DISPUTED}')
           AND confidence >= ?
        {_RANKING}
         LIMIT 400
        """,
        (min_confidence, now),
    )

    candidates = []

    wanted = set(topic.split())

    for row in rows:
        stored_topic = (row["topic"] or "").lower()

        score = 0.0

        if stored_topic == topic:
            score += 1.0
        elif wanted:
            stored_words = set(stored_topic.split())

            shared = len(wanted & stored_words)

            if shared == 0:
                continue

            score += shared / max(len(wanted), len(stored_words)) * 0.9

        score += overlap(query, f"{row['claim']} {row['topic']}") * 0.4

        stale = bool(row["stale_after"]) and row["stale_after"] <= now

        if stale and require_fresh:
            continue

        if row["status"] == DISPUTED:
            score *= 0.5

        candidates.append((score, stale, dict(row)))

    candidates.sort(key=lambda item: item[0], reverse=True)

    matches = [row for score, _stale, row in candidates if score >= 0.34]

    selected = matches[:limit]

    for row in selected:
        database.execute(
            "UPDATE knowledge SET hits = hits + 1, last_used = ? WHERE id = ?",
            (now, row["id"]),
        )

    return selected


def stale_rows(limit: int = 40) -> list[dict]:
    """Rows the updater must re-verify now."""
    now = iso(now_utc())

    rows = database.fetchall(
        f"""
        SELECT * FROM knowledge
         WHERE status != '{RETIRED}'
           AND (
                status = '{STALE}'
             OR stale_after IS NULL
             OR stale_after <= ?
           )
        ORDER BY COALESCE(verified_at, created_at) ASC
         LIMIT ?
        """,
        (now, int(limit)),
    )

    return [dict(row) for row in rows]


def recent_changes(limit: int = 10) -> list[dict]:
    rows = database.fetchall(
        """
        SELECT * FROM knowledge_history
         ORDER BY id DESC
         LIMIT ?
        """,
        (int(limit),),
    )

    return [dict(row) for row in rows]


def stats() -> dict:
    row = database.fetchone(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END), 0) AS active,
            COALESCE(SUM(CASE WHEN status = 'stale' THEN 1 ELSE 0 END), 0) AS stale,
            COALESCE(SUM(CASE WHEN status = 'disputed' THEN 1 ELSE 0 END), 0) AS disputed,
            COALESCE(SUM(CASE WHEN stale_after IS NOT NULL AND stale_after <= ?
                     THEN 1 ELSE 0 END), 0) AS due,
            ROUND(AVG(confidence), 3) AS mean_confidence,
            MAX(COALESCE(verified_at, created_at)) AS newest,
            MIN(COALESCE(verified_at, created_at)) AS oldest,
            COALESCE(SUM(hits), 0) AS uses
        FROM knowledge
        """,
        (iso(now_utc()),),
    )

    return dict(row or {})


# ==========================================
# Topics / watchlist
# ==========================================

def record_topic(query: str, *, user_id: int | None = None):
    """Track what people ask so the updater keeps useful topics warm."""
    topic = topic_of(query)

    if not topic or len(topic) < 4:
        return

    now = iso(now_utc())

    # A topic is worth re-verifying once it has been asked three times and has
    # not been refreshed in the last six hours.
    database.execute(
        """
        INSERT INTO topics(topic, sample, asked_count, first_seen, last_asked)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(topic) DO UPDATE SET
            asked_count = topics.asked_count + 1,
            last_asked = excluded.last_asked,
            sample = excluded.sample,
            watch = CASE
                WHEN topics.asked_count + 1 >= 3
                     AND (
                            topics.last_refresh IS NULL
                         OR topics.last_refresh <= ?
                     )
                THEN 1
                ELSE topics.watch
            END
        """,
        (
            topic,
            query[:280],
            now,
            now,
            iso(now_utc() - timedelta(hours=6)),
        ),
    )


def watchlist(limit: int = 12) -> list[dict]:
    rows = database.fetchall(
        """
        SELECT * FROM topics
         WHERE watch = 1
         ORDER BY asked_count DESC, last_asked DESC
         LIMIT ?
        """,
        (int(limit),),
    )

    return [dict(row) for row in rows]


def top_topics(limit: int = 10) -> list[dict]:
    rows = database.fetchall(
        """
        SELECT topic, asked_count, last_asked, watch, last_refresh
          FROM topics
         ORDER BY asked_count DESC, last_asked DESC
         LIMIT ?
        """,
        (int(limit),),
    )

    return [dict(row) for row in rows]


def mark_refreshed(topic: str):
    database.execute(
        """
        UPDATE topics
           SET last_refresh = ?, refresh_count = refresh_count + 1, watch = 0
         WHERE topic = ?
        """,
        (iso(now_utc()), topic),
    )


def clear_all() -> int:
    """Admin helper: wipe learned knowledge (user facts are untouched)."""
    removed = database.execute_count("DELETE FROM knowledge")

    logger.warning("Knowledge base cleared (%s rows).", removed)

    return removed
