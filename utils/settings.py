"""
Project Nexus

Settings Manager

Provides centralized access to all
application settings.
"""

from config import (
    PROJECT_NAME,
    VERSION,
    DISCORD_TOKEN,
    GEMINI_API_KEY,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    DATABASE_NAME,
    MEMORY_LIMIT,
    DEBUG,
    LOG_LEVEL,
)


class Settings:
    def __init__(self):
        self.project_name = PROJECT_NAME
        self.version = VERSION

        self.discord_token = DISCORD_TOKEN

        self.gemini_api_key = GEMINI_API_KEY
        self.provider = DEFAULT_PROVIDER
        self.model = DEFAULT_MODEL

        self.database_name = DATABASE_NAME
        self.memory_limit = MEMORY_LIMIT

        self.debug = DEBUG
        self.log_level = LOG_LEVEL


settings = Settings()
