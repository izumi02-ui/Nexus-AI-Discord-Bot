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

    conn.commit()
    conn.close()


def save_message(user_id, role, message):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO memories(user_id, role, message)
        VALUES (?, ?, ?)
        """,
        (user_id, role, message)
    )

    conn.commit()
    conn.close()


def load_memory(user_id, limit=20):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, message
        FROM memories
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit)
    )

    rows = cursor.fetchall()

    conn.close()

    rows.reverse()

    return [
        {
            "role": role,
            "content": message
        }
        for role, message in rows
    ]


def clear_memory_db(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM memories WHERE user_id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()
