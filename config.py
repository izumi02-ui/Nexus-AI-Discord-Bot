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
# AI API Keys
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
# Local AI
# ==========================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434"
)

LMSTUDIO_URL = os.getenv(
    "LMSTUDIO_URL",
    "http://127.0.0.1:1234/v1"
)

# ==========================================
# Default Provider
# ==========================================

DEFAULT_PROVIDER = os.getenv(
    "DEFAULT_PROVIDER",
    "gemini"
)

# ==========================================
# AI Models
# ==========================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5"
)

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemma-3-27b-it:free"
)

CLAUDE_MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-sonnet-4"
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-chat"
)

MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL",
    "mistral-large-latest"
)

COHERE_MODEL = os.getenv(
    "COHERE_MODEL",
    "command-a"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:4b"
)

LMSTUDIO_MODEL = os.getenv(
    "LMSTUDIO_MODEL",
    "qwen3-4b"
)

# ==========================================
# Media APIs
# ==========================================

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY"
)

SPOTIFY_CLIENT_ID = os.getenv(
    "SPOTIFY_CLIENT_ID"
)

SPOTIFY_CLIENT_SECRET = os.getenv(
    "SPOTIFY_CLIENT_SECRET"
)

# ==========================================
# Optional APIs
# ==========================================

GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN"
)

REDDIT_CLIENT_ID = os.getenv(
    "REDDIT_CLIENT_ID"
)

REDDIT_CLIENT_SECRET = os.getenv(
    "REDDIT_CLIENT_SECRET"
)

REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT"
)

NEWS_API_KEY = os.getenv(
    "NEWS_API_KEY"
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
