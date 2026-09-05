# 馃寣 Project Nexus

**An AI companion for Discord that would rather say *"I could not verify that"* than guess.**

It runs on free or local models, and the guarantee comes from the pipeline around the model - not from the model itself.

`Nexus 1.4.0-alpha.V4` 路 Python 3.11 路 discord.py 路 FastAPI 路 SQLite 路 Lavalink

---

## Table of contents

- [What Nexus is](#what-nexus-is)
- [What it has today](#what-it-has-today)
- [Changing the AI agent](#changing-the-ai-agent) - swap provider, swap model, add your own
- [Commands](#commands)
- [Music and live voice](#music-and-live-voice)
- [Evidence sources](#evidence-sources)
- [Files, images, PDFs and media](#files-images-pdfs-and-media)
- [Configuration](#configuration)
- [Planned features](#planned-features)
- [Running it](#running-it)
- [Tests](#tests)
- [Project layout](#project-layout)
- [Notes on honesty](#notes-on-honesty)

---

## What Nexus is

```
you: who is the prime minister of india?
nexus: [Answers with the name and date found in the live evidence.]
       -# Sources
       -# Source A: <https://...> 路 Source B: <https://...>
       -# 鈿欙笍 verified 路 2 domains 路 freshness: today 路 1.9s
```

Every message goes through the same seven steps:

**route 鈫� recall 鈫� retrieve 鈫� compose 鈫� answer 鈫� verify 鈫� learn**

1. **route** - does this even need looking up? A price does; "why is the sky blue" does not.
2. **recall** - has Nexus already verified something that answers it?
3. **retrieve** - ask several sources at once, rank them, cross-check them.
4. **compose** - build the prompt: persona, evidence, verified notes, your facts, memory.
5. **answer** - one call to whichever model is configured, with failover.
6. **verify** - compare the draft with the evidence: invented links deleted, unverified figures capped, "I can't access the internet" rewritten, one repair pass.
7. **learn** - keep the exchange, the durable facts, and the verified answer - with an expiry date on anything that can go stale.

---

## What it has today

| Area | Shipped |
|---|---|
| **Accuracy** | freshness policy (`instant` / `short` / `medium` / `long` / `static`), multi-source retrieval, cross-domain corroboration, conflict detection, post-generation verification, one bounded retry, honest disclosure under each answer |
| **Self-updating** | a background cycle that re-verifies stale knowledge, probes every evidence tool with a real query, refreshes runtime facts (version, provider, model, UTC + IST clock), keeps hot topics warm, prunes weak rows - and repairs retired model ids against live provider catalogues |
| **Memory** | per-user conversation window, durable facts with provenance and supersede-history, user-facing `/facts` `/remember` `/forget` |
| **Knowledge store** | verified claims with confidence, hit counts, expiry, `disputed` state, and a full change history (`knowledge_history`) |
| **Providers** | OpenRouter, OpenAI, Gemini, Claude, Groq, DeepSeek, Mistral, Cohere, Ollama, LM Studio - capability-aware fallback with failure breakers (a rate-limited provider is cooled down, not swallowed silently) |
| **Tools** | 23 evidence modules as separate files, each declaring its own TTL, keywords, required keys and health (14 usable with no keys) |
| **Discord** | slash commands + prefix commands; natural no-mention DMs; server mentions and direct replies; idle presence; attachments recognised; per-user cooldowns; cog auto-loading; startup-safe `/health` endpoint for Render |
| **Music** | Lavalink v4 playback with 25 slash commands, queues, playlists, controls, seek, loop, filters, autoplay, per-guild state and automatic idle cleanup; YouTube/Spotify links are resolved by the media node |
| **Live voice** | opt-in turn-based voice conversations: Discord PCM 鈫� Groq Whisper 鈫� the existing verified Nexus engine 鈫� Groq Orpheus female speech; bounded buffers, consent notice and no audio persistence |
| **Rich responses** | ordinary conversation stays plain; substantial explanations and worked solutions use a plain introduction, focused embed and plain conclusion; retrieved HTTPS reference images appear only when a source supplies one; generated code uses fenced, copy-friendly embeds and attaches a complete file when it exceeds Discord's embed limit |
| **API** | FastAPI app mirroring the same pipeline (`/chat` `/search` `/research` `/memory` `/tools` `/models` `/health`), returning grounding metadata so a web client can show a "verified" badge too |
| **Safety** | prompt-injection framing for all quoted content, fabricated-citation removal, path-confined file reads, `@everyone` neutralisation on output, code-fence-safe message splitting, AST-only calculator |

Not shipped (placeholder tools the pipeline skips rather than trusts): image understanding, OCR, image generation. See [Planned features](#planned-features).

---

## Changing the AI agent

This is the part you asked for: **the model is a plug, not the product.** Everything above keeps working whichever one you point at, because routing, retrieval and verification are provider-independent.

### 1. Swap provider or model - one file, no code

`.env`:

```bash
# which provider answers by default
DEFAULT_PROVIDER=openrouter

# OpenRouter: a comma-separated chain, primary first, each tried in order
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODELS=google/gemma-3-27b-it:free,x-ai/grok-3-mini:free,openrouter/free

# or a direct provider
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash

# or no cloud at all - local
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b
```

Rules the pipeline follows:

- the model chain is tried left to right; a provider that errors is put on a 2-minute cooldown and the **next** one answers - the default is never permanently repointed
- `MODEL_AUTO_REFRESH=true` means Nexus re-reads `/models` on each provider and swaps a model id that got retired, for that session only
- **`config.py` is never rewritten by the bot.** A restart always goes back to what you committed - no silent self-modification

### 2. Switch live, without restarting

```
/nexus provider            鈫� list providers, availability, model, breaker state
/nexus provider groq       鈫� switch for the rest of this session
/nexus provider reset      鈫� clear failure counters
/nexus models              鈫� re-read catalogues and repair model ids
/nexus status              鈫� what is answering right now, and how grounded it is being
```

### 3. Change the personality

`prompts/` - loaded per request, in order: `base.txt` 鈫� `personality.txt` 鈫� `creator.txt` 鈫� `accuracy.txt`, then a runtime block generated from the live process (clock, version, provider, tool inventory).

### 4. Add a brand-new agent (one file + two lines)

Contract: `ai/providers/base.py` - `name`, `model`, `capabilities`, `available`, `ask(user_id, conversation) -> str`, `use_tool(tool, query)`.

```python
# ai/providers/myagent.py
from typing import Dict, List

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider
from utils.settings import settings


class MyAgentProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "MyAgent"

    @property
    def model(self) -> str:
        return settings.myagent_model

    @property
    def capabilities(self):
        # What this agent can actually do. The router reads these flags:
        # a provider without `vision` is never asked to describe an image,
        # and one with `web_search` can ground itself instead of using tools.
        return ProviderCapabilities(
            vision=False,
            files=False,
            web_search=False,
            image_generation=False,
            function_calling=True,
            streaming=True,
            reasoning=True,
        )

    @property
    def available(self) -> bool:
        return bool(settings.myagent_api_key)

    async def ask(self, user_id: int, conversation: List[Dict]) -> str:
        response = ...  # one call; raise on error, the manager handles fallback
        return response.text.strip()

    async def use_tool(self, tool: str, query: str):
        raise NotImplementedError(f"{tool} is not implemented for MyAgent")
```

```python
# ai/provider_manager.py  鈫� inside _register()
self._add("myagent", MyAgentProvider)

# ai/provider_manager.py  鈫� QUALITY_ORDER (where it sits in the fallback chain)
QUALITY_ORDER = [..., "myagent", "ollama", "lmstudio"]
```

plus `MYAGENT_API_KEY` / `MYAGENT_MODEL` in `config.py` and `utils/settings.py`.

That's all: it appears in `/nexus provider`, participates in failover, is health-reported, and inherits the verifier - a new agent cannot bypass accuracy.

**Available capability flags:** `web_search`, `vision`, `files`, `image_generation`, `code_execution`, `function_calling`, `streaming`, `reasoning`, `embeddings`, `audio`, `video`. Most are declared-but-unused today; they exist so a stronger agent can advertise what it can do and the pipeline can use it instead of faking it.

---

## Commands

| Command | What it does |
|---|---|
| `/ask <question>` | the full pipeline, with a grounding badge |
| `/search <query> [tool]` | the raw evidence, before any model touches it |
| `/sources` | what Nexus' last answer to you was built on |
| `/verify <claim>` | checks one statement live: supported / only-one-place / sources disagree |
| `/remember` 路 `/forget` 路 `/facts` | control over what it keeps about you (`/forget all` wipes it) |
| `/tools` 路 `/version` 路 `/ping` | which sources are configured 路 which build is running 路 how fast |
| `/nexus status` | provider, grounded rate, cache, knowledge store, updater state |
| `/nexus reverify [topic]` | re-check stored knowledge right now |
| `/nexus accuracy [preset]` | `strict` / `balanced` / `fast` / `offline`, or fine-grained flags |
| `/nexus tools` 路 `/nexus models` | per-tool health and cooldowns 路 re-read provider model lists |
| `/nexus provider` 路 `/nexus knowledge` 路 `/nexus start-updating` | rotate providers 路 inspect the store 路 run a cycle |

Prefix equivalents `!ai`, `!memory`, `!status` work where slash commands don't.
In a server, mention Nexus or reply directly to one of its messages. In a DM,
send a normal message鈥攎entioning the bot is optional. Valid prefix commands are
handled once and are not duplicated as AI conversation replies.

---

## Music and live voice

Nexus' nickname is **Nexy**. Music and conversational voice are optional and
disabled independently, so the normal AI bot still starts when either media
service is unconfigured.

### Music

Music runs through a separate Lavalink v4 service. `/music play` accepts a
search term, direct track URL or playlist URL; Spotify links are matched to a
playable audio source by LavaSrc rather than streamed from Spotify itself.

| Playback | Queue and control |
|---|---|
| `/music join`, `play`, `playnext`, `pause`, `resume`, `skip`, `previous`, `replay`, `stop`, `disconnect` | `/music queue`, `nowplaying`, `remove`, `move`, `jump`, `shuffle`, `clear`, `loop`, `volume`, `seek`, `autoplay`, `filter`, `status`, `help` |

Queues and locks are isolated per guild. Nexus disconnects when the last human
leaves or the inactive timeout expires, and releases the player state. It does
not expose lyric-copying or media-download commands.

### Live conversation

`/voice join` starts an explicitly confirmed, near-real-time conversation in
the caller's channel. Nexus transcribes one finished turn, asks the same AI
engine used by text chat, and speaks the result using the configured female
voice. `/voice mute`, `/voice unmute`, `/voice say`, `/voice status` and
`/voice leave` control the session. Audio is held only in a bounded memory
buffer and discarded after transcription. Transcribed text follows the normal
Nexus conversation-memory policy; `VOICE_TRANSCRIPTS` separately controls
whether a readable copy is posted in the command channel. Spoken turns are
kept within Orpheus' 200-character request limit; the text copy can remain
detailed.

Discord permits one voice connection per bot per guild, so music and live
conversation switch modes cleanly rather than attempting to speak over each
other. Different guilds remain independent. Full deployment and privacy notes
are in [`docs/MEDIA.md`](docs/MEDIA.md).

---

## Evidence sources

Twenty-three tool modules in `tools/` - **14 answer with no keys at all**, and the two intentional placeholders (`ocr`, `vision`) are skipped rather than trusted. "Needs a key" is not a failure: Nexus says so, skips the source, and tells you which tools failed alongside the answer.

| Source | Key | What it's for |
|---|---|---|
| `weather` (Open-Meteo) | - | current conditions + forecast, geocoded |
| `currency` | - | FX rates, conversions |
| `time` | - | clocks and time zones by place |
| `calculator` | - | exact arithmetic (never the model's mental maths) |
| `maps` (OSM Nominatim) | - | places, addresses, distances |
| `wikipedia` | - | stable reference, with page timestamps |
| `news` (publisher RSS) | - | headlines with real publish dates; non-feed pages are refused |
| `brave` / `google` / `web_search` | optional key/provider | proper web results; Brave is paid and is skipped cleanly when unset |
| `duckduckgo` | - | Instant Answer API (HTML search is CAPTCHA-gated, so it isn't scraped) |
| `web_scraper` | - | read a URL a user pasted, as quoted untrusted text |
| `github` | optional | repos, issues, releases |
| `stackoverflow` | - | real answers, accepted-first |
| `arxiv` | - | papers with dates |
| `reddit` | approved OAuth credentials | community reports labelled as low-authority; unidentified public JSON access is not used |
| `steam` | - | prices and store pages |
| `spotify` / `youtube` | key | tracks, videos |
| `translator` | - | optional self-hosted LibreTranslate, otherwise free MyMemory fallback |
| `file_reader` | opt-in | plain-text files inside `data/uploads` only |
| `ocr` / `vision` | - | **placeholders, `implemented = False`** - skipped by the pipeline, reported as unavailable |

---

## Files, images, PDFs and media

What happens with an attachment **today**:

1. The router notices attachments and stops treating the message as a plain question.
2. Links and pages are fetched by `web_scraper`; text files inside the upload directory are read by `file_reader` (`FILE_READER_ENABLED=true`, path-confined).
3. Images are **not** described. If the active provider has no `vision` capability, Nexus says so and asks for the text instead of inventing a caption - the prompt states this rule and the verifier will not let an ungrounded image description stand as verified.

What it needs to become what you want it to be - each item below is scoped as a real change, in [Planned features](#planned-features).

---

## Configuration

Decided in `config.py`, overridable by environment variables. Nothing hidden, nothing rewritten at runtime.

```bash
# accuracy
SEARCH_MODE=auto               # auto | always | never
SEARCH_TIMEOUT=18              # deadline for the whole evidence phase
MAX_SOURCES=6
MIN_SOURCES_FOR_GROUNDING=2    # independent domains needed to call it verified
VERIFICATION_ENABLED=true
AUTO_RETRY_WITH_SEARCH=true    # one repair pass when an answer cannot stand
REFUSE_WHEN_UNVERIFIED=true    # prefer refusal over guessing a "right now" fact
CITATION_MODE=auto             # auto | footer | inline | off
OPENROUTER_WEB_SEARCH=true     # live search for fresh questions; may use credits
OPENROUTER_SEARCH_RESULTS=5

# self-update
SELF_UPDATE_ENABLED=true
SELF_UPDATE_INTERVAL=21600     # re-verify stale knowledge every 6 hours
KNOWLEDGE_TTL=86400
KNOWLEDGE_MAX_ENTRIES=2000
KNOWLEDGE_MIN_CONFIDENCE=0.35
TOOL_PROBE_INTERVAL=1800       # health-check tools with a real query
MODEL_AUTO_REFRESH=true        # repair retired model ids

# memory & files
DATABASE_NAME=data/nexus.db
MEMORY_LIMIT=20
FILE_READER_ENABLED=false
FILE_READER_ROOT=data/uploads

# discord
DISCORD_TOKEN=...
COMMAND_GUILD_ID=              # one guild = instant slash-command propagation

# music (requires a separate Lavalink v4 service)
MUSIC_ENABLED=true
LAVALINK_URI=http://your-lavalink-service:2333
LAVALINK_PASSWORD=change-me
MUSIC_DEFAULT_VOLUME=75

# live voice (requires GROQ_API_KEY)
VOICE_CHAT_ENABLED=true
VOICE_STT_MODEL=whisper-large-v3-turbo
VOICE_TTS_MODEL=canopylabs/orpheus-v1-english
VOICE_TTS_VOICE=hannah
```

The complete, deduplicated template is [`.env.example`](.env.example). It lists
all 90 supported environment variables exactly once, including every direct
provider, local provider, retrieval service, accuracy control, memory setting,
media option and Render health option. Copy it to `.env`; never commit real
tokens.

Full annotated list: [`.env.example`](.env.example). Reasoning per knob: [`docs/ACCURACY.md`](docs/ACCURACY.md).

---

## Planned features

Ordered by accuracy/utility per unit of work. **None of these exist yet** - the tools marked "placeholder" above are the stubs they grow out of, and the pipeline already skips a stub instead of trusting it, which is why adding them is additive rather than a rewrite.

### 1. Image understanding (vision) 鈥� next up

- **User sees:** "what's in this screenshot?" answered with the UI text, the error, the chart's numbers - and which part is read vs inferred.
- **How:** providers that support images get the bytes (`capabilities.vision`); `ai/engine.py` already passes attachments and refuses to guess when no vision provider is active. The missing piece is the multimodal message shape per provider.
- **Depends on:** an existing key (OpenAI/Gemini/OpenRouter vision model). No new Python dependency.
- **Guardrail:** the verifier's existing "cite only what the evidence contains" rule extends to image text - an unread image yields "I could not read that", never a caption.

### 2. OCR fallback for text in images

- **User sees:** screenshots, terminal photos and scanned pages become quoted text, attributed to "OCR, low confidence".
- **How:** implement `tools/ocr.py` for real (flip `implemented = True`), used when no vision model is available.
- **Depends on:** `pytesseract` is already in `requirements.txt`; needs the Tesseract binary on the host (`apt install tesseract-ocr`) - so it must stay optional and report unavailable when missing.

### 3. PDF: read, quote, and view

- **User sees:** `/nexus pdf <url|attachment>` 鈫� per-page summary with page-number citations ("p.4: the method reports a 12% gain"), plus a rendered preview link; ask follow-ups grounded in that document.
- **How:** new `tools/pdf_reader.py`: extract text per page, index it as evidence so `SearchReport` citations point at `doc.pdf#page=4`, feed the ranked pages through the same compose/verify path.
- **Depends on:** the **first new dependency** in this project (`pypdf` for text; optional `pdf2image` + `poppler` for actual rendered previews).
- **Guardrail:** text is quoted-untrusted like the web scraper, size and page caps, no execution of embedded JS, and PDFs from the internet are labelled as unverified single-source documents.

### 4. File understanding beyond plain text

- **User sees:** a repo archive, a `.jsonl` export, a spreadsheet or a log file answered with real numbers, not vibes.
- **How:** widen `tools/file_reader.py` (which today is text-suffix-only and path-confined) with CSV/table summarising, code-file structure extraction, and chunked map-reduce over long documents so a 400-page file still yields citable parts.
- **Depends on:** stdlib `csv`/`json` first; `pandas` only if table analytics become a goal (it's a heavy add).
- **Guardrail:** the existing root confinement stays, per-user isolated directories, and every file-derived claim carries the file name.

### 5. Image generation

- **User sees:** `/imagine a lighthouse in a storm, watercolour` 鈫� an image posted back with the prompt it used and which provider/model made it.
- **How:** `capabilities.image_generation`