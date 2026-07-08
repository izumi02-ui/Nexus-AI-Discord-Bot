"""
Project Nexus

Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# Project
# ============================================

PROJECT_NAME = "Project Nexus"
VERSION = "2.0.0-alpha.1"

# ============================================
# Discord
# ============================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ============================================
# AI
# ============================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-2.5-flash"

# ============================================
# Database
# ============================================

DATABASE_NAME = "data/nexus.db"

# ============================================
# Memory
# ============================================

MEMORY_LIMIT = 20

# ============================================
# Logging
# ============================================

DEBUG = True
LOG_LEVEL = "INFO"

# ============================================
# Creator
# ============================================

CREATOR_ID = 1169870987135823876

CREATOR_NAMES = [
    "Izumi",
    "Rohit",
    "IZ"
]

# ============================================
# Special Users
# ============================================

SPECIAL_USERS = {
    1465041186325794939: {
        "display_name": "Ash",
        "nicknames": [
            "Ash",
            "Ashey"
        ]
    }
}
