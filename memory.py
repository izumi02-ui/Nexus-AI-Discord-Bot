from collections import defaultdict

# Maximum number of messages to remember
MAX_MEMORY = 20

# Stores conversations for each user
user_memories = defaultdict(list)


def add_message(user_id: int, role: str, content: str):
    """
    Adds a message to the user's memory.
    """

    user_memories[user_id].append({
        "role": role,
        "content": content
    })

    # Keep only the latest messages
    if len(user_memories[user_id]) > MAX_MEMORY:
        user_memories[user_id] = user_memories[user_id][-MAX_MEMORY:]


def get_memory(user_id: int):
    """
    Returns the user's conversation history.
    """
    return user_memories[user_id]


def clear_memory(user_id: int):
    """
    Clears the user's memory.
    """
    user_memories[user_id] = []
