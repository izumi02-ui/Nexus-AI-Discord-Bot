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
VERSION = "1.4.0-alpha.V4"


# ==========================================
# Discord
# ==========================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NEXUS_NICKNAME = os.getenv("NEXUS_NICKNAME", "Nexy").strip() or "Nexy"


# ==========================================
# AI API Keys
# ==========================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")


# ==========================================
# Default Provider
# ==========================================

DEFAULT_PROVIDER = os.getenv(
    "DEFAULT_PROVIDER",
    "openrouter",
)


# ==========================================
# OpenRouter Models
# Ordered from primary to final fallback
# ==========================================

_openrouter_models = os.getenv(
    "OPENROUTER_MODELS",
    "google/gemma-3-27b-it:free,openrouter/free",
)

OPENROUTER_MODELS = [
    model.strip()
    for model in _openrouter_models.split(",")
    if model.strip()
]

if not OPENROUTER_MODELS:
    OPENROUTER_MODELS = ["openrouter/free"]

# Kept for compatibility with existing code.
OPENROUTER_MODEL = OPENROUTER_MODELS[0]


# ==========================================
# Other AI Models
# ==========================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5",
)

CLAUDE_MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-sonnet-4",
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-chat",
)

MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL",
    "mistral-large-latest",
)

COHERE_MODEL = os.getenv(
    "COHERE_MODEL",
    "command-a",
)


# ==========================================
# Local AI
# ==========================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:4b",
)

LMSTUDIO_URL = os.getenv(
    "LMSTUDIO_URL",
    "http://127.0.0.1:1234/v1",
)

LMSTUDIO_MODEL = os.getenv(
    "LMSTUDIO_MODEL",
    "qwen3-4b",
)


# ==========================================
# Search Evidence APIs
# Every one of these is optional. Nexus still works without them - the
# aggregator simply skips whatever is not configured.
# ==========================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


# ==========================================
# Optional APIs
# ==========================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

#: Brave Search API - the single biggest accuracy upgrade available.
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

#: Optional self-hosted translation server used before MyMemory.
LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL")

#: Extra RSS feeds merged into the news tool (comma separated "name|url").
NEWS_FEEDS = os.getenv("NEWS_FEEDS", "")


def _feed_list() -> dict:
    feeds = {}

    for entry in NEWS_FEEDS.split(","):
        if "|" not in entry:
            continue

        name, _, url = entry.partition("|")

        if name.strip() and url.strip().startswith("http"):
            feeds[name.strip()] = url.strip()

    return feeds


NEWS_FEED_MAP = _feed_list()


# ==========================================
# Database
# ==========================================

DATABASE_NAME = os.getenv(
    "DATABASE_NAME",
    "data/nexus.db",
)


# ==========================================
# Memory
# ==========================================

MEMORY_LIMIT = int(
    os.getenv("MEMORY_LIMIT", "20")
)


# ==========================================
# Accuracy Pipeline
# ==========================================


def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


# ==========================================
# Voice and Music
# ==========================================

# Music is streamed by an external Lavalink v4 node. Spotify's Web API exposes
# metadata, not audio; a LavaSrc-enabled node resolves Spotify/Apple/Deezer
# URLs to playable tracks without Nexus scraping media itself.
MUSIC_ENABLED = _flag("MUSIC_ENABLED", "true")
LAVALINK_URI = os.getenv("LAVALINK_URI", "").strip().rstrip("/")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "").strip()
LAVALINK_IDENTIFIER = os.getenv("LAVALINK_IDENTIFIER", "nexus-main").strip()
LAVALINK_INACTIVE_TIMEOUT = int(os.getenv("LAVALINK_INACTIVE_TIMEOUT", "300"))
MUSIC_DEFAULT_VOLUME = max(0, min(200, int(os.getenv("MUSIC_DEFAULT_VOLUME", "75"))))
MUSIC_MAX_QUEUE = max(10, min(1000, int(os.getenv("MUSIC_MAX_QUEUE", "250"))))
MUSIC_DJ_ROLE = os.getenv("MUSIC_DJ_ROLE", "DJ").strip()
MUSIC_ANNOUNCE_TRACKS = _flag("MUSIC_ANNOUNCE_TRACKS", "true")

# Live voice is turn-based: receive PCM -> Groq Whisper -> Nexus -> Groq
# Orpheus. Audio is kept in memory only until its turn has been transcribed.
VOICE_CHAT_ENABLED = _flag("VOICE_CHAT_ENABLED", "true")
VOICE_STT_MODEL = os.getenv("VOICE_STT_MODEL", "whisper-large-v3-turbo").strip()
VOICE_TTS_MODEL = os.getenv(
    "VOICE_TTS_MODEL", "canopylabs/orpheus-v1-english"
).strip()
VOICE_TTS_VOICE = os.getenv("VOICE_TTS_VOICE", "hannah").strip()
VOICE_TTS_SPEED = max(0.5, min(2.0, float(os.getenv("VOICE_TTS_SPEED", "1.0"))))
VOICE_LANGUAGE = os.getenv("VOICE_LANGUAGE", "").strip().lower()
VOICE_SILENCE_SECONDS = max(
    0.4, min(3.0, float(os.getenv("VOICE_SILENCE_SECONDS", "0.9")))
)
VOICE_MIN_UTTERANCE_SECONDS = max(
    0.2, min(3.0, float(os.getenv("VOICE_MIN_UTTERANCE_SECONDS", "0.5")))
)
VOICE_MAX_UTTERANCE_SECONDS = max(
    3.0, min(60.0, float(os.getenv("VOICE_MAX_UTTERANCE_SECONDS", "20")))
)
# Groq Orpheus currently accepts at most 200 input characters per request.
VOICE_MAX_REPLY_CHARS = max(
    80, min(200, int(os.getenv("VOICE_MAX_REPLY_CHARS", "190")))
)
# Post a readable voice-turn mirror in the command channel. The normal AI
# engine memory policy applies to transcribed text independently.
VOICE_TRANSCRIPTS = _flag("VOICE_TRANSCRIPTS", "true")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "").strip()


#: auto = decide per question, always = search every prompt, never = chat only.
SEARCH_MODE = os.getenv("SEARCH_MODE", "auto").lower()

#: Hard deadline for the whole evidence phase, so a dead API cannot stall a reply.
SEARCH_TIMEOUT = float(
    os.getenv("SEARCH_TIMEOUT", os.getenv("AI_REQUEST_TIMEOUT", "18"))
)

#: How many sources to collect, and how many independent ones are required
#: before Nexus may state something as verified fact.
MAX_SOURCES = int(os.getenv("MAX_SOURCES", "6"))
MIN_SOURCES_FOR_GROUNDING = int(os.getenv("MIN_SOURCES_FOR_GROUNDING", "2"))

#: Compare the finished answer against the evidence before sending it.
VERIFICATION_ENABLED = _flag("VERIFICATION_ENABLED", "true")

#: If a time-sensitive question was answered with no evidence, re-run it once
#: with search results attached instead of shipping the guess.
AUTO_RETRY_WITH_SEARCH = _flag("AUTO_RETRY_WITH_SEARCH", "true")

#: auto | footer | inline | off - how sources are shown to the user.
CITATION_MODE = os.getenv("CITATION_MODE", "auto").lower()

#: For instant/short freshness questions, refuse to answer when nothing was
#: verified, rather than guessing.
REFUSE_WHEN_UNVERIFIED = _flag("REFUSE_WHEN_UNVERIFIED", "true")

#: Let OpenRouter supply live search evidence for fresh questions. This can
#: consume OpenRouter credits; set it to false to use only Nexus' keyless tools.
OPENROUTER_WEB_SEARCH = _flag("OPENROUTER_WEB_SEARCH", "true")

OPENROUTER_SEARCH_RESULTS = int(os.getenv("OPENROUTER_SEARCH_RESULTS", "5"))

#: Cache TTLs shrink to the query's freshness budget when enabled.
CACHE_FRESHNESS_AWARE = _flag("CACHE_FRESHNESS_AWARE", "true")

#: Prompt budget for retrieved evidence.
MAX_CONTEXT_SOURCES = int(os.getenv("MAX_CONTEXT_SOURCES", "5"))
EVIDENCE_CHAR_BUDGET = int(os.getenv("EVIDENCE_CHAR_BUDGET", "9000"))


# ==========================================
# Memory
# ==========================================

#: Ask the model to extract durable facts when no rule matched. Costs one
#: extra (small) provider call per message, so it is opt-in.
MEMORY_LLM_EXTRACTION = _flag("MEMORY_LLM_EXTRACTION", "false")

#: Re-verify remembered facts that have not been confirmed for this long.
FACT_REVIEW_INTERVAL = int(os.getenv("FACT_REVIEW_INTERVAL", str(30 * 24 * 3600)))


# ==========================================
# Local File Access
# ==========================================

#: Directory Nexus is allowed to read text files from. Off unless enabled:
#: an AI tool that can read any path is a data leak waiting for a prompt.
FILE_READER_ROOT = os.getenv("FILE_READER_ROOT", "data/uploads")

FILE_READER_ENABLED = _flag("FILE_READER_ENABLED", "false")


# ==========================================
# Self-Update
# ==========================================

#: Master switch for the background knowledge updater.
SELF_UPDATE_ENABLED = _flag("SELF_UPDATE_ENABLED", "true")

#: How often verified knowledge is re-checked and refreshed (seconds).
SELF_UPDATE_INTERVAL = int(os.getenv("SELF_UPDATE_INTERVAL", str(6 * 3600)))

#: Default lifetime of a knowledge entry before it must be re-verified.
KNOWLEDGE_TTL = int(os.getenv("KNOWLEDGE_TTL", str(24 * 3600)))

KNOWLEDGE_MAX_ENTRIES = int(os.getenv("KNOWLEDGE_MAX_ENTRIES", "2000"))

#: Entries below this confidence are pruned instead of injected into a prompt.
KNOWLEDGE_MIN_CONFIDENCE = float(os.getenv("KNOWLEDGE_MIN_CONFIDENCE", "0.35"))

#: How often tools are probed and provider health is refreshed (seconds).
TOOL_PROBE_INTERVAL = int(os.getenv("TOOL_PROBE_INTERVAL", str(30 * 60)))

#: Re-read each provider's model list and repair the fallback chain when a
#: configured model id disappears (OpenRouter, and any OpenAI-compatible API).
MODEL_AUTO_REFRESH = _flag("MODEL_AUTO_REFRESH", "true")

#: How many of the most-asked topics are kept warm by the updater.
WATCHLIST_LIMIT = int(os.getenv("WATCHLIST_LIMIT", "12"))

#: Refresh the pinned runtime facts (date, version, provider, tool health).
RUNTIME_FACTS_INTERVAL = int(os.getenv("RUNTIME_FACTS_INTERVAL", "900"))


# ==========================================
# Logging
# ==========================================

DEBUG = os.getenv(
    "DEBUG",
    "true",
).lower() in {"1", "true", "yes", "on"}

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
)


# ==========================================
# Creator
# ==========================================

#: Optional guild id. When set, slash commands are registered in that server
#: only, which makes them appear instantly while developing; when empty they
#: are registered globally and can take up to an hour to propagate.
COMMAND_GUILD_ID = os.getenv("COMMAND_GUILD_ID", "")

CREATOR_ID = int(os.getenv("CREATOR_ID", "1169870987135823876"))

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
