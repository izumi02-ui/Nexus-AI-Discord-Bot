"""
Project Nexus

Settings Manager

Central place for reading
configuration values.
"""

from config import (
    DISCORD_TOKEN,
    GEMINI_API_KEY,
)


class Settings:

    def __init__(self):

        self.discord_token = DISCORD_TOKEN

        self.gemini_api_key = GEMINI_API_KEY

        self.default_provider = "gemini"

        self.model = "gemini-2.5-flash"

        self.memory_limit = 20

        self.debug = True


settings = Settings()
