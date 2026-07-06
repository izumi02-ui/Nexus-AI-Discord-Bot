import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is missing!")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found. AI features will be disabled.")
