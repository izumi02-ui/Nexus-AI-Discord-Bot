import sqlite3

DATABASE_NAME = "nexus.db"


def connect():
    return sqlite3.connect(DATABASE_NAME)


def setup_database():
    conn = connect()
    cursor = conn.cursor()

    # Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Chat Memory
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Server Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servers(
        guild_id INTEGER PRIMARY KEY,
        prefix TEXT DEFAULT '!',
        personality TEXT DEFAULT 'default'
    )
    """)

    conn.commit()
    conn.close()
