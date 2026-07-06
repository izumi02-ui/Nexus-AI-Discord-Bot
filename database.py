import sqlite3

DATABASE_NAME = "nexus.db"

MAX_MEMORY = 40
MAX_FACTS = 100


def connect():
    return sqlite3.connect(DATABASE_NAME, timeout=10)


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

    # User Facts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_facts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        fact TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# ============================
# Chat Memory
# ============================

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

    # Keep only the newest MAX_MEMORY messages
    cursor.execute(
        """
        DELETE FROM memories
        WHERE user_id=?
        AND id NOT IN (
            SELECT id
            FROM memories
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
        )
        """,
        (user_id, user_id, MAX_MEMORY)
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


# ============================
# User Facts
# ============================

def save_fact(user_id, fact):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM user_facts
        WHERE user_id=? AND fact=?
        """,
        (user_id, fact)
    )

    if cursor.fetchone() is None:

        cursor.execute(
            """
            INSERT INTO user_facts(user_id, fact)
            VALUES (?, ?)
            """,
            (user_id, fact)
        )

        # Keep only newest MAX_FACTS facts
        cursor.execute(
            """
            DELETE FROM user_facts
            WHERE user_id=?
            AND id NOT IN (
                SELECT id
                FROM user_facts
                WHERE user_id=?
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (user_id, user_id, MAX_FACTS)
        )

        conn.commit()

    conn.close()


def get_facts(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT fact
        FROM user_facts
        WHERE user_id=?
        ORDER BY id ASC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]


def clear_facts(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM user_facts WHERE user_id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()