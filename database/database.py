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

        Path("data").mkdir(
            exist_ok=True
        )

        self.connection = sqlite3.connect(
            DATABASE_NAME
        )

        self.connection.row_factory = sqlite3.Row

        self.cursor = self.connection.cursor()

        logger.info("Database connected.")

    def execute(
        self,
        query: str,
        params=()
    ):

        self.cursor.execute(
            query,
            params
        )

        self.connection.commit()

    def fetchone(
        self,
        query: str,
        params=()
    ):

        self.cursor.execute(
            query,
            params
        )

        return self.cursor.fetchone()

    def fetchall(
        self,
        query: str,
        params=()
    ):

        self.cursor.execute(
            query,
            params
        )

        return self.cursor.fetchall()

    def setup(self):

        logger.info("Creating database tables...")

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

        self.execute("""
        CREATE TABLE IF NOT EXISTS facts(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            fact TEXT
        )
        """)

        logger.info("Database ready.")


database = Database()


def setup_database():

    database.setup()
