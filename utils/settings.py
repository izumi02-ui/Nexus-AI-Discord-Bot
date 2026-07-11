"""
Project Nexus

Settings Manager
"""

from config import *


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
        # Provider
        # =====================================

        self.provider = DEFAULT_PROVIDER

        # =====================================
        # API Keys
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
        # Models
        # =====================================

        self.gemini_model = GEMINI_MODEL
        self.openai_model = OPENAI_MODEL
        self.openrouter_model = OPENROUTER_MODEL
        self.claude_model = CLAUDE_MODEL
        self.groq_model = GROQ_MODEL
        self.deepseek_model = DEEPSEEK_MODEL
        self.mistral_model = MISTRAL_MODEL
        self.cohere_model = COHERE_MODEL
        self.ollama_model = OLLAMA_MODEL
        self.lmstudio_model = LMSTUDIO_MODEL

        # =====================================
        # Local
        # =====================================

        self.ollama_url = OLLAMA_URL
        self.lmstudio_url = LMSTUDIO_URL

        # =====================================
        # Database
        # =====================================

        self.database_name = DATABASE_NAME
        self.memory_limit = MEMORY_LIMIT

        # =====================================
        # Logging
        # =====================================

        self.debug = DEBUG
        self.log_level = LOG_LEVEL


settings = Settings()
