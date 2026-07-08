"""
Project Nexus

Database Manager

Handles the SQLite connection and
database initialization.
"""

import sqlite3
from pathlib import Path

from config import DATABASE_NAME
from utils.logger import logger


class Database:

    def __init__(self):

        Path("data").mkdir(exist_ok=True)

        self.connection = sqlite3.connect(
            DATABASE_NAME,
            check_same_thread=False
        )

        self.connection.row_factory = sqlite3.Row

        logger.info("Database connected.")

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
        # Facts
        # ==========================

        self.execute("""
        CREATE TABLE IF NOT EXISTS facts(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            fact TEXT
        )
        """)

        # ==========================
        # Memories
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

        logger.info(
            "Database ready."
        )


database = Database()


def setup_database():

    database.setup()
