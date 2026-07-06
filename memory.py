from database import (
    save_message,
    load_memory,
    clear_memory_db
)


def add_message(user_id, role, content):
    save_message(user_id, role, content)


def get_memory(user_id):
    return load_memory(user_id)


def clear_memory(user_id):
    clear_memory_db(user_id)
