"""
Project Nexus

Configuration
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ==========================================
# Project
# ==========================================

PROJECT_NAME = "Project Nexus"
VERSION = "2.0.0-alpha.1"

# ==========================================
# Discord
# ==========================================

DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

# ==========================================
# AI Providers
# ==========================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

CLAUDE_API_KEY = os.getenv(
    "CLAUDE_API_KEY"
)

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY"
)

MISTRAL_API_KEY = os.getenv(
    "MISTRAL_API_KEY"
)

COHERE_API_KEY = os.getenv(
    "COHERE_API_KEY"
)

# ==========================================
# Local Providers
# ==========================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

LMSTUDIO_URL = os.getenv(
    "LMSTUDIO_URL",
    "http://localhost:1234/v1"
)

# ==========================================
# Default AI
# ==========================================

DEFAULT_PROVIDER = os.getenv(
    "DEFAULT_PROVIDER",
    "gemini"
)

DEFAULT_MODEL = os.getenv(
    "DEFAULT_MODEL",
    "gemini-2.5-flash"
)

# ==========================================
# Database
# ==========================================

DATABASE_NAME = "data/nexus.db"

# ==========================================
# Memory
# ==========================================

MEMORY_LIMIT = 20

# ==========================================
# Logging
# ==========================================

DEBUG = True

LOG_LEVEL = "INFO"

# ==========================================
# Creator
# ==========================================

CREATOR_ID = 1169870987135823876

CREATOR_NAMES = [

    "Izumi",

    "Rohit",

    "IZ",

]

# ==========================================
# Special Users
# ==========================================

SPECIAL_USERS = {

    1465041186325794939: {

        "display_name": "Ash",

        "nicknames": [

            "Ash",

            "Ashey",

        ],

    }

}
