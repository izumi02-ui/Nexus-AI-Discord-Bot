"""
Project Nexus

Database Manager

Handles the SQLite connection and database initialization.

The schema is versioned and migrates in place: Nexus is a long-running bot with
a database its owner cannot easily hand-edit, so new accuracy columns are added
on startup instead of asking anyone to run a migration script.
"""

import sqlite3
from pathlib import Path

from config import DATABASE_NAME
from utils.logger import logger

SCHEMA_VERSION = 3

import re


def fact_key(fact: str) -> str:
    """
    Stable dedupe key for a fact: the part before the colon, slugified.

    "Lives in: Delhi" and "Lives in: Mumbai" share the key "lives_in", so the
    newer one replaces the older instead of stacking a contradiction.
    """
    head = str(fact or "").partition(":")[0]

    return re.sub(r"[^a-z0-9]+", "_", head.lower()).strip("_") or "fact"


class Database:

    def __init__(self):

        Path(self._directory()).mkdir(exist_ok=True, parents=True)

        self.connection = sqlite3.connect(
            DATABASE_NAME,
            check_same_thread=False
        )

        self.connection.row_factory = sqlite3.Row

        # WAL keeps reads from blocking the writer when the updater loop and a
        # command hit the database at the same moment.
        try:
            self.connection.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:  # pragma: no cover - unsupported on some FS
            pass

        self.connection.execute("PRAGMA foreign_keys=ON")

        logger.info("Database connected.")

    @staticmethod
    def _directory() -> str:
        return str(Path(DATABASE_NAME).parent)

    def execute(
        self,
        query: str,
        params=()
    ):

        cursor = self.connection.cursor()

        cursor.execute(
            query,
            params
        )

        self.connection.commit()

    def execute_count(
        self,
        query: str,
        params=()
    ) -> int:
        """Run a statement and report how many rows it touched."""

        cursor = self.connection.cursor()

        cursor.execute(query, params)

        self.connection.commit()

        return cursor.rowcount or 0

    def executemany(self, query, seq):
        cursor = self.connection.cursor()

        cursor.executemany(query, seq)

        self.connection.commit()

    def fetchone(
        self,
        query: str,
        params=()
    ):

        cursor = self.connection.cursor()

        cursor.execute(
            query,
            params
        )

        return cursor.fetchone()

    def fetchall(
        self,
        query: str,
        params=()
    ):

        cursor = self.connection.cursor()

        cursor.execute(
            query,
            params
        )

        return cursor.fetchall()

    # ==========================================
    # Schema
    # ==========================================

    def setup(self):

        logger.info(
            "Creating database tables..."
        )

        # ==========================
        # Profiles
        # ==========================

        self.execute("""
        CREATE TABLE IF NOT EXISTS profiles(

            user_id INTEGER PRIMARY KEY,

            username TEXT,

            display_name TEXT,

            role TEXT,

            created_at TEXT,

            last_seen TEXT,

            total_messages INTEGER DEFAULT 0
        )
        """)

        # ==========================
        # Facts (what Nexus knows about a person)
        # ==========================

        self.execute("""
        CREATE TABLE IF NOT EXISTS facts(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            fact TEXT,

            category TEXT,

            key TEXT,

            confidence REAL DEFAULT 1.0,

            source TEXT DEFAULT 'conversation',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            superseded INTEGER DEFAULT 0
        )
        """)

        self.execute("""
        CREATE INDEX IF NOT EXISTS idx_facts_user
        ON facts(user_id, superseded)
        """)

        # ==========================
        # Memories (recent conversation)
        # ==========================

        self.execute("""
        CREATE TABLE IF NOT EXISTS memories(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            role TEXT,

            content TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # ==========================
        # Knowledge (verified world facts with provenance + TTL)
        # ==========================

        self.execute("""
        CREATE TABLE IF NOT EXISTS knowledge(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            topic TEXT NOT NULL,

            claim TEXT NOT NULL DEFAULT '',

            value TEXT NOT NULL,

            source TEXT,

            url TEXT,

            tool TEXT,

            confidence REAL DEFAULT 0.8,

            verified_at TEXT,

            stale_after TEXT,

            ttl_seconds INTEGER,

            hits INTEGER DEFAULT 0,

            last_used TEXT,

            user_id INTEGER,

            status TEXT DEFAULT 'active',

            notes TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(topic, claim)
        )
        """)

        self.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_status
        ON knowledge(status, stale_after)
        """)

        # Every correction is written down, so a wrong fact can be audited
        # instead of silently overwritten.
        self.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            topic TEXT,

            claim TEXT,

            old_value TEXT,

            new_value TEXT,

            reason TEXT,

            source TEXT,

            changed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # What the community keeps asking about - drives the self-updater.
        self.execute("""
        CREATE TABLE IF NOT EXISTS topics(

            topic TEXT PRIMARY KEY,

            sample TEXT,

            asked_count INTEGER DEFAULT 1,

            unique_users INTEGER DEFAULT 1,

            first_seen TEXT DEFAULT CURRENT_TIMESTAMP,

            last_asked TEXT,

            watch INTEGER DEFAULT 0,

            last_refresh TEXT,

            refresh_count INTEGER DEFAULT 0
        )
        """)

        self.execute("""
        CREATE TABLE IF NOT EXISTS tool_health(

            tool TEXT PRIMARY KEY,

            available INTEGER,

            successes INTEGER DEFAULT 0,

            failures INTEGER DEFAULT 0,

            last_error TEXT,

            last_ok TEXT,

            last_sample INTEGER,

            checked_at TEXT,

            note TEXT
        )
        """)

        # Cross-run bookkeeping for the updater (last cycle, model catalog...).
        self.execute("""
        CREATE TABLE IF NOT EXISTS app_state(

            key TEXT PRIMARY KEY,

            value TEXT,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Corrections users gave Nexus, kept for audit and re-learning.
        self.execute("""
        CREATE TABLE IF NOT EXISTS feedback(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            kind TEXT,

            query TEXT,

            answer TEXT,

            note TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self._migrate()

        # PRAGMA does not accept bound parameters.
        self.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")

        logger.info(
            "Database ready (schema v%s).",
            SCHEMA_VERSION,
        )

    # ==========================================
    # Migrations
    # ==========================================

    def _migrate(self):
        """Add missing columns to pre-existing tables."""
        additions = {
            "facts": {
                "category": "TEXT",
                "key": "TEXT",
                "confidence": "REAL DEFAULT 1.0",
                "source": "TEXT DEFAULT 'conversation'",
                "updated_at": "TEXT",
                "superseded": "INTEGER DEFAULT 0",
            },
            "profiles": {
                "preferences": "TEXT",
            },
            "topics": {
                "unique_users": "INTEGER DEFAULT 1",
                "last_refresh": "TEXT",
                "refresh_count": "INTEGER DEFAULT 0",
            },
        }

        for table, columns in additions.items():
            existing = {
                row["name"]
                for row in self.fetchall(f"PRAGMA table_info({table})")
            }

            for column, definition in columns.items():
                if column in existing:
                    continue

                self.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )

                logger.info(
                    "Migrated %s: added %s",
                    table,
                    column,
                )

        # Backfill a dedupe key for facts stored before keys existed so the
        # "update, never duplicate" rule works on old rows too.
        rows = self.fetchall(
            "SELECT id, fact, created_at FROM facts "
            "WHERE key IS NULL OR key = ''"
        )

        for row in rows:
            self.execute(
                "UPDATE facts SET key = ?, updated_at = ? WHERE id = ?",
                (
                    fact_key(row["fact"]),
                    row["created_at"],
                    row["id"],
                ),
            )

    # ==========================================
    # Key/value state
    # ==========================================

    def get_state(self, key: str, default=None):
        row = self.fetchone(
            "SELECT value FROM app_state WHERE key = ?",
            (key,),
        )

        return row["value"] if row else default

    def set_state(self, key: str, value):
        self.execute(
            """
            INSERT INTO app_state(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value)),
        )

    def clear_state(self, key: str):
        self.execute("DELETE FROM app_state WHERE key = ?", (key,))


database = Database()


def setup_database():

    database.setup()
