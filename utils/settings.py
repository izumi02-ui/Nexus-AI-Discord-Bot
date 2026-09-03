"""
Project Nexus

Settings Manager
"""

from config import (
    PROJECT_NAME,
    VERSION,
    DISCORD_TOKEN,
    DEFAULT_PROVIDER,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    CLAUDE_API_KEY,
    GROQ_API_KEY,
    DEEPSEEK_API_KEY,
    MISTRAL_API_KEY,
    COHERE_API_KEY,
    GEMINI_MODEL,
    OPENAI_MODEL,
    OPENROUTER_MODEL,
    OPENROUTER_MODELS,
    CLAUDE_MODEL,
    GROQ_MODEL,
    DEEPSEEK_MODEL,
    MISTRAL_MODEL,
    COHERE_MODEL,
    OLLAMA_URL,
    OLLAMA_MODEL,
    LMSTUDIO_URL,
    LMSTUDIO_MODEL,
    DATABASE_NAME,
    MEMORY_LIMIT,
    DEBUG,
    LOG_LEVEL,
)


class Settings:
    def __init__(self):
        # Project
        self.project_name = PROJECT_NAME
        self.version = VERSION

        # Discord
        self.discord_token = DISCORD_TOKEN

        # Default provider
        self.provider = DEFAULT_PROVIDER

        # API keys
        self.gemini_api_key = GEMINI_API_KEY
        self.openai_api_key = OPENAI_API_KEY
        self.openrouter_api_key = OPENROUTER_API_KEY
        self.claude_api_key = CLAUDE_API_KEY
        self.groq_api_key = GROQ_API_KEY
        self.deepseek_api_key = DEEPSEEK_API_KEY
        self.mistral_api_key = MISTRAL_API_KEY
        self.cohere_api_key = COHERE_API_KEY

        # Models
        self.gemini_model = GEMINI_MODEL
        self.openai_model = OPENAI_MODEL

        self.openrouter_model = OPENROUTER_MODEL
        self.openrouter_models = list(OPENROUTER_MODELS)

        self.claude_model = CLAUDE_MODEL
        self.groq_model = GROQ_MODEL
        self.deepseek_model = DEEPSEEK_MODEL
        self.mistral_model = MISTRAL_MODEL
        self.cohere_model = COHERE_MODEL

        # Local AI
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL
        self.lmstudio_url = LMSTUDIO_URL
        self.lmstudio_model = LMSTUDIO_MODEL

        # Database and memory
        self.database_name = DATABASE_NAME
        self.memory_limit = MEMORY_LIMIT

        # Logging
        self.debug = DEBUG
        self.log_level = LOG_LEVEL


settings = Settings()