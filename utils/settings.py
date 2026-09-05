"""
Project Nexus

Settings Manager
"""

from config import (
    PROJECT_NAME,
    VERSION,
    DISCORD_TOKEN,
    NEXUS_NICKNAME,
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
    MEMORY_LLM_EXTRACTION,
    FACT_REVIEW_INTERVAL,
    DEBUG,
    LOG_LEVEL,
    # Evidence sources
    BRAVE_API_KEY,
    YOUTUBE_API_KEY,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    GITHUB_TOKEN,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    NEWS_API_KEY,
    GNEWS_API_KEY,
    NEWS_FEED_MAP,
    LIBRETRANSLATE_URL,
    # Accuracy pipeline
    SEARCH_MODE,
    SEARCH_TIMEOUT,
    MAX_SOURCES,
    MIN_SOURCES_FOR_GROUNDING,
    VERIFICATION_ENABLED,
    AUTO_RETRY_WITH_SEARCH,
    CITATION_MODE,
    REFUSE_WHEN_UNVERIFIED,
    CACHE_FRESHNESS_AWARE,
    OPENROUTER_WEB_SEARCH,
    OPENROUTER_SEARCH_RESULTS,
    MAX_CONTEXT_SOURCES,
    EVIDENCE_CHAR_BUDGET,
    # Self-update
    SELF_UPDATE_ENABLED,
    SELF_UPDATE_INTERVAL,
    KNOWLEDGE_TTL,
    KNOWLEDGE_MAX_ENTRIES,
    KNOWLEDGE_MIN_CONFIDENCE,
    TOOL_PROBE_INTERVAL,
    MODEL_AUTO_REFRESH,
    WATCHLIST_LIMIT,
    RUNTIME_FACTS_INTERVAL,
    FILE_READER_ROOT,
    FILE_READER_ENABLED,
    MUSIC_ENABLED,
    LAVALINK_URI,
    LAVALINK_PASSWORD,
    LAVALINK_IDENTIFIER,
    LAVALINK_INACTIVE_TIMEOUT,
    MUSIC_DEFAULT_VOLUME,
    MUSIC_MAX_QUEUE,
    MUSIC_DJ_ROLE,
    MUSIC_ANNOUNCE_TRACKS,
    MUSIC_START_GRACE_SECONDS,
    MUSIC_SPOTIFY_FALLBACK,
    MUSIC_NODE_PROBE_TIMEOUT,
    VOICE_CHAT_ENABLED,
    VOICE_STT_MODEL,
    VOICE_TTS_PROVIDER,
    VOICE_TTS_MODEL,
    VOICE_TTS_VOICE,
    VOICE_TTS_SPEED,
    VOICE_TTS_TEXT_FALLBACK,
    VOICE_LANGUAGE,
    VOICE_SILENCE_SECONDS,
    VOICE_MIN_UTTERANCE_SECONDS,
    VOICE_MAX_UTTERANCE_SECONDS,
    VOICE_RMS_THRESHOLD,
    VOICE_DUPLICATE_WINDOW_SECONDS,
    VOICE_ERROR_COOLDOWN_SECONDS,
    VOICE_MAX_REPLY_CHARS,
    VOICE_TRANSCRIPTS,
    FFMPEG_PATH,
)


class Settings:
    def __init__(self):
        # Project
        self.project_name = PROJECT_NAME
        self.version = VERSION

        # Discord
        self.discord_token = DISCORD_TOKEN
        self.nexus_nickname = NEXUS_NICKNAME

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
        self.memory_llm_extraction = MEMORY_LLM_EXTRACTION
        self.fact_review_interval = FACT_REVIEW_INTERVAL

        # Evidence sources
        self.brave_api_key = BRAVE_API_KEY
        self.youtube_api_key = YOUTUBE_API_KEY
        self.spotify_client_id = SPOTIFY_CLIENT_ID
        self.spotify_client_secret = SPOTIFY_CLIENT_SECRET
        self.github_token = GITHUB_TOKEN
        self.reddit_client_id = REDDIT_CLIENT_ID
        self.reddit_client_secret = REDDIT_CLIENT_SECRET
        self.reddit_user_agent = REDDIT_USER_AGENT
        self.news_api_key = NEWS_API_KEY
        self.gnews_api_key = GNEWS_API_KEY
        self.news_feeds = dict(NEWS_FEED_MAP)
        self.libretranslate_url = LIBRETRANSLATE_URL
        self.file_reader_root = FILE_READER_ROOT
        self.file_reader_enabled = FILE_READER_ENABLED

        # Discord voice and music
        self.music_enabled = MUSIC_ENABLED
        self.lavalink_uri = LAVALINK_URI
        self.lavalink_password = LAVALINK_PASSWORD
        self.lavalink_identifier = LAVALINK_IDENTIFIER
        self.lavalink_inactive_timeout = LAVALINK_INACTIVE_TIMEOUT
        self.music_default_volume = MUSIC_DEFAULT_VOLUME
        self.music_max_queue = MUSIC_MAX_QUEUE
        self.music_dj_role = MUSIC_DJ_ROLE
        self.music_announce_tracks = MUSIC_ANNOUNCE_TRACKS
        self.music_start_grace_seconds = MUSIC_START_GRACE_SECONDS
        self.music_spotify_fallback = MUSIC_SPOTIFY_FALLBACK
        self.music_node_probe_timeout = MUSIC_NODE_PROBE_TIMEOUT
        self.voice_chat_enabled = VOICE_CHAT_ENABLED
        self.voice_stt_model = VOICE_STT_MODEL
        self.voice_tts_provider = VOICE_TTS_PROVIDER
        self.voice_tts_model = VOICE_TTS_MODEL
        self.voice_tts_voice = VOICE_TTS_VOICE
        self.voice_tts_speed = VOICE_TTS_SPEED
        self.voice_tts_text_fallback = VOICE_TTS_TEXT_FALLBACK
        self.voice_language = VOICE_LANGUAGE
        self.voice_silence_seconds = VOICE_SILENCE_SECONDS
        self.voice_min_utterance_seconds = VOICE_MIN_UTTERANCE_SECONDS
        self.voice_max_utterance_seconds = VOICE_MAX_UTTERANCE_SECONDS
        self.voice_rms_threshold = VOICE_RMS_THRESHOLD
        self.voice_duplicate_window_seconds = VOICE_DUPLICATE_WINDOW_SECONDS
        self.voice_error_cooldown_seconds = VOICE_ERROR_COOLDOWN_SECONDS
        self.voice_max_reply_chars = VOICE_MAX_REPLY_CHARS
        self.voice_transcripts = VOICE_TRANSCRIPTS
        self.ffmpeg_path = FFMPEG_PATH

        # Accuracy pipeline
        self.search_mode = SEARCH_MODE
        self.search_timeout = SEARCH_TIMEOUT
        self.max_sources = MAX_SOURCES
        self.min_sources_for_grounding = MIN_SOURCES_FOR_GROUNDING
        self.verification_enabled = VERIFICATION_ENABLED
        self.auto_retry_with_search = AUTO_RETRY_WITH_SEARCH
        self.citation_mode = CITATION_MODE
        self.refuse_when_unverified = REFUSE_WHEN_UNVERIFIED
        self.cache_freshness_aware = CACHE_FRESHNESS_AWARE
        self.openrouter_web_search = OPENROUTER_WEB_SEARCH
        self.openrouter_search_results = OPENROUTER_SEARCH_RESULTS
        self.max_context_sources = MAX_CONTEXT_SOURCES
        self.evidence_char_budget = EVIDENCE_CHAR_BUDGET

        # Self-update
        self.self_update_enabled = SELF_UPDATE_ENABLED
        self.self_update_interval = SELF_UPDATE_INTERVAL
        self.knowledge_ttl = KNOWLEDGE_TTL
        self.knowledge_max_entries = KNOWLEDGE_MAX_ENTRIES
        self.knowledge_min_confidence = KNOWLEDGE_MIN_CONFIDENCE
        self.tool_probe_interval = TOOL_PROBE_INTERVAL
        self.model_auto_refresh = MODEL_AUTO_REFRESH
        self.watchlist_limit = WATCHLIST_LIMIT
        self.runtime_facts_interval = RUNTIME_FACTS_INTERVAL

        # Logging
        self.debug = DEBUG
        self.log_level = LOG_LEVEL

    # ======================================
    # Runtime overrides
    # ======================================

    def update(self, **values):
        """
        Change settings for the running process.

        Used by the self-updating layer (provider health, model chain) and by
        admin commands. Values are in-memory only - persistent settings live in
        the settings table so a restart cannot quietly change behaviour.
        """
        changed = {}

        for key, value in values.items():
            if not hasattr(self, key):
                raise AttributeError(f"Unknown setting: {key}")

            previous = getattr(self, key)

            setattr(self, key, value)

            changed[key] = (previous, value)

        return changed

    def snapshot(self) -> dict:
        """Everything that affects answers, for /status and the API."""
        return {
            "provider": self.provider,
            "search_mode": self.search_mode,
            "verification": self.verification_enabled,
            "auto_retry": self.auto_retry_with_search,
            "citation_mode": self.citation_mode,
            "min_sources_for_grounding": self.min_sources_for_grounding,
            "search_timeout": self.search_timeout,
            "file_reader_enabled": self.file_reader_enabled,
            "self_update": self.self_update_enabled,
            "self_update_interval": self.self_update_interval,
            "knowledge_ttl": self.knowledge_ttl,
            "model_auto_refresh": self.model_auto_refresh,
            "music_enabled": self.music_enabled,
            "lavalink_configured": bool(
                self.lavalink_uri and self.lavalink_password
            ),
            "voice_chat_enabled": self.voice_chat_enabled,
            "voice_speech_configured": bool(self.groq_api_key),
        }


settings = Settings()
