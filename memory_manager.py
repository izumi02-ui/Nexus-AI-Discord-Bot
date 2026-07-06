from database import save_fact


KEYWORDS = [
    "my name is",
    "call me",
    "i like",
    "i love",
    "my favorite",
    "i am",
    "i'm",
    "i use",
    "i prefer",
]


def process_message(user_id, message):

    text = message.lower()

    for keyword in KEYWORDS:

        if keyword in text:
            save_fact(user_id, message)
            return True

    return False
