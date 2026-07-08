"""
Project Nexus

Settings Manager
"""

from config import *

class Settings:

    discord_token = DISCORD_TOKEN

    gemini_api_key = GEMINI_API_KEY

    provider = DEFAULT_PROVIDER

    model = DEFAULT_MODEL

    memory_limit = MEMORY_LIMIT

    debug = DEBUG

settings = Settings()
