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
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    CLAUDE_API_KEY,
    GROQ_API_KEY,
    DEEPSEEK_API_KEY,
    MISTRAL_API_KEY,
    COHERE_API_KEY,

    OLLAMA_URL,
    LMSTUDIO_URL,

    DEFAULT_PROVIDER,
    DEFAULT_MODEL,

    DATABASE_NAME,
    MEMORY_LIMIT,

    DEBUG,
    LOG_LEVEL,
)


class Settings:

    def __init__(self):

        # =====================================
        # Project
        # =====================================

        self.project_name = PROJECT_NAME
        self.version = VERSION

        # =====================================
        # Discord
        # =====================================

        self.discord_token = DISCORD_TOKEN

        # =====================================
        # AI Providers
        # =====================================

        self.gemini_api_key = GEMINI_API_KEY
        self.openai_api_key = OPENAI_API_KEY
        self.openrouter_api_key = OPENROUTER_API_KEY
        self.claude_api_key = CLAUDE_API_KEY
        self.groq_api_key = GROQ_API_KEY
        self.deepseek_api_key = DEEPSEEK_API_KEY
        self.mistral_api_key = MISTRAL_API_KEY
        self.cohere_api_key = COHERE_API_KEY

        # =====================================
        # Local Providers
        # =====================================

        self.ollama_url = OLLAMA_URL
        self.lmstudio_url = LMSTUDIO_URL

        # =====================================
        # Defaults
        # =====================================

        self.provider = DEFAULT_PROVIDER
        self.model = DEFAULT_MODEL

        # =====================================
        # Database
        # =====================================

        self.database_name = DATABASE_NAME
        self.memory_limit = MEMORY_LIMIT

        # =====================================
        # Debug
        # =====================================

        self.debug = DEBUG
        self.log_level = LOG_LEVEL


settings = Settings()
