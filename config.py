import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Special Users
IZUMI_ID = 1169870987135823876
ASH_ID = 1465041186325794939

SPECIAL_USERS = {
    IZUMI_ID: {
        "display_name": "Izumi",
        "nicknames": ["IZ", "Rohit"],
    },

    ASH_ID: {
        "display_name": "Ash",
        "nicknames": ["Ashey"],
    },
}

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is missing!")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing!")
