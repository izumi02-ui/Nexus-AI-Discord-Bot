# 🌌 Project Nexus

**An AI companion for Discord that would rather say *"I could not verify that"* than guess.**

It runs on free or local models, and the guarantee comes from the pipeline around the model - not from the model itself.

`Nexus 1.4.0-alpha.V4` · Python 3.11 · discord.py · FastAPI · SQLite · Lavalink

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
       -# Source A: <https://...> · Source B: <https://...>
       -# ⚙️ verified · 2 domains · freshness: today · 1.9s
```

Every message goes through the same seven steps:

**route → recall → retrieve → compose → answer → verify → learn**

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
| **Live voice** | opt-in turn-based voice conversations: Discord PCM → Groq Whisper → the existing verified Nexus engine → Groq Orpheus female speech; bounded buffers, consent notice and no audio persistence |
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
/nexus provider            → list providers, availability, model, breaker state
/nexus provider groq       → switch for the rest of this session
/nexus provider reset      → clear failure counters
/nexus models              → re-read catalogues and repair model ids
/nexus status              → what is answering right now, and how grounded it is being
```

### 3. Change the personality

`prompts/` - loaded per request, in order: `base.txt` → `personality.txt` → `creator.txt` → `accuracy.txt`, then a runtime block generated from the live process (clock, version, provider, tool inventory).

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
# ai/provider_manager.py  → inside _register()
self._add("myagent", MyAgentProvider)

# ai/provider_manager.py  → QUALITY_ORDER (where it sits in the fallback chain)
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
| `/remember` · `/forget` · `/facts` | control over what it keeps about you (`/forget all` wipes it) |
| `/tools` · `/version` · `/ping` | which sources are configured · which build is running · how fast |
| `/nexus status` | provider, grounded rate, cache, knowledge store, updater state |
| `/nexus reverify [topic]` | re-check stored knowledge right now |
| `/nexus accuracy [preset]` | `strict` / `balanced` / `fast` / `offline`, or fine-grained flags |
| `/nexus tools` · `/nexus models` | per-tool health and cooldowns · re-read provider model lists |
| `/nexus provider` · `/nexus knowledge` · `/nexus start-updating` | rotate providers · inspect the store · run a cycle |

Prefix equivalents `!ai`, `!memory`, `!status` work where slash commands don't.
In a server, mention Nexus or reply directly to one of its messages. In a DM,
send a normal message—mentioning the bot is optional. Valid prefix commands are
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
detailed. A configurable RMS gate rejects Discord silence/keepalive frames
before transcription, and identical per-speaker transcripts are suppressed
inside a short safety window. If Groq requires model-term approval, Nexus
keeps listening active, preserves the generated text reply, and shows one
actionable TTS notice instead of repeating the provider error every turn.

Discord permits one voice connection per bot per guild, so music and live
conversation switch modes through a shared per-guild handoff rather than
opening competing clients. Music also probes each Lavalink node for LavaSrc,
Spotify and modern YouTube support, and delays Now Playing cards past immediate
source failures. Different guilds remain independent. Full deployment and
privacy notes are in [`docs/MEDIA.md`](docs/MEDIA.md).

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
MUSIC_SPOTIFY_FALLBACK=true

# live voice (requires GROQ_API_KEY)
VOICE_CHAT_ENABLED=true
VOICE_STT_MODEL=whisper-large-v3-turbo
VOICE_TTS_PROVIDER=groq
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=hannah
VOICE_TTS_TEXT_FALLBACK=true
VOICE_RMS_THRESHOLD=250
VOICE_DUPLICATE_WINDOW_SECONDS=12
```

The complete, deduplicated template is [`.env.example`](.env.example). It lists
the supported environment variables exactly once, including every direct
provider, local provider, retrieval service, accuracy control, memory setting,
media option and Render health option. Copy it to `.env`; never commit real
tokens.

Full annotated list: [`.env.example`](.env.example). Reasoning per knob: [`docs/ACCURACY.md`](docs/ACCURACY.md).

---

## Planned features

Ordered by accuracy/utility per unit of work. **None of these exist yet** - the tools marked "placeholder" above are the stubs they grow out of, and the pipeline already skips a stub instead of trusting it, which is why adding them is additive rather than a rewrite.

### 1. Image understanding (vision) — next up

- **User sees:** "what's in this screenshot?" answered with the UI text, the error, the chart's numbers - and which part is read vs inferred.
- **How:** providers that support images get the bytes (`capabilities.vision`); `ai/engine.py` already passes attachments and refuses to guess when no vision provider is active. The missing piece is the multimodal message shape per provider.
- **Depends on:** an existing key (OpenAI/Gemini/OpenRouter vision model). No new Python dependency.
- **Guardrail:** the verifier's existing "cite only what the evidence contains" rule extends to image text - an unread image yields "I could not read that", never a caption.

### 2. OCR fallback for text in images

- **User sees:** screenshots, terminal photos and scanned pages become quoted text, attributed to "OCR, low confidence".
- **How:** implement `tools/ocr.py` for real (flip `implemented = True`), used when no vision model is available.
- **Depends on:** `pytesseract` is already in `requirements.txt`; needs the Tesseract binary on the host (`apt install tesseract-ocr`) - so it must stay optional and report unavailable when missing.

### 3. PDF: read, quote, and view

- **User sees:** `/nexus pdf <url|attachment>` → per-page summary with page-number citations ("p.4: the method reports a 12% gain"), plus a rendered preview link; ask follow-ups grounded in that document.
- **How:** new `tools/pdf_reader.py`: extract text per page, index it as evidence so `SearchReport` citations point at `doc.pdf#page=4`, feed the ranked pages through the same compose/verify path.
- **Depends on:** the **first new dependency** in this project (`pypdf` for text; optional `pdf2image` + `poppler` for actual rendered previews).
- **Guardrail:** text is quoted-untrusted like the web scraper, size and page caps, no execution of embedded JS, and PDFs from the internet are labelled as unverified single-source documents.

### 4. File understanding beyond plain text

- **User sees:** a repo archive, a `.jsonl` export, a spreadsheet or a log file answered with real numbers, not vibes.
- **How:** widen `tools/file_reader.py` (which today is text-suffix-only and path-confined) with CSV/table summarising, code-file structure extraction, and chunked map-reduce over long documents so a 400-page file still yields citable parts.
- **Depends on:** stdlib `csv`/`json` first; `pandas` only if table analytics become a goal (it's a heavy add).
- **Guardrail:** the existing root confinement stays, per-user isolated directories, and every file-derived claim carries the file name.

### 5. Image generation

- **User sees:** `/imagine a lighthouse in a storm, watercolour` → an image posted back with the prompt it used and which provider/model made it.
- **How:** `capabilities.image_generation` already exists for exactly this; add `tools/image_gen.py` + a `/generate` command, sending the result as `discord.File`.
- **Depends on:** a provider key that generates (OpenAI images, Gemini/Imagen, Stability, Fal). A keyless path exists (e.g. `https://image.pollinations.ai/prompt/...`) but it returned HTTP 500 when checked from this environment, so **treat it as unverified** and don't build the default path on it.
- **Guardrail:** no public-figure or real-person likenesses, no sexual/violent content, visible provenance that it is AI-generated, and a rate limit separate from chat so one user cannot burn the quota.

### 6. Animation: images and video to GIF

- **User sees:** `/gif from <url-or-attachment> 3s` → a small looped GIF; or "make these 4 frames into a gif".
- **How:** `tools/media_render.py`. Still images → GIF is doable with **Pillow, already a dependency** (resize, frame delay, palette quantisation, size cap). Video → GIF needs `ffmpeg`, which is a system binary, so it must degrade to a clear "ffmpeg is not installed here" rather than fail silently - and clip sources must be user-supplied bytes or a licensed source, not scraped downloads.
- **Depends on:** Pillow (have) · `ffmpeg` binary (optional, host-level) · *not* `yt-dlp`: pulling media out of platforms is a terms-of-service problem, so plan around user-uploaded files.
- **Guardrail:** output size/duration caps, ephemeral temp files, and content moderation before posting to a public channel.

### 7. Retrieval upgrades that make all of the above better

- `BRAVE_API_KEY` / `GEMINI_API_KEY` wired into a labeled "eval set" (`tests/` question → expected source), so ranking changes are measured, not eyeballed.
- Per-tool timeouts (weather 4 s, Wikipedia 8 s) and early exit once two domains agree.
- `/nexus history` - the knowledge change log already exists in `knowledge_history`; nobody can read it yet.
- Scheduled digests: "the thing you asked about changed" - watchlist, history and diffing are all built already.

### Explicitly not planned

Self-modifying code execution without a human review step. Scraping services whose terms forbid it. Silent writes to `config.py`.

---

## Running it

```bash
git clone https://github.com/izumi02-ui/Nexus-AI-Discord-Bot
cd Nexus-AI-Discord-Bot

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env       # DISCORD_TOKEN, then a provider key if you want one
python bot.py
```

**Zero keys still works.** With only `DISCORD_TOKEN`, Nexus answers from Ollama/LM Studio if either is running, uses the keyless evidence sources, and tells you when an answer is not verified.

<details>
<summary>Discord setup</summary>

1. [Developer Portal](https://discord.com/developers/applications) → New Application → Bot.
2. Enable **Message Content** and **Server Members** intents (privileged).
3. Copy the token into `.env` as `DISCORD_TOKEN`.
4. Invite with `bot` + `applications.commands` scopes and grant `Send Messages`,
   `Read Message History`, `Embed Links`, `Connect`, `Speak` and `Use Voice
   Activity`. Stage channels additionally require permission to request to speak.

</details>

### Render / free tier

`Procfile` runs `python bot.py`; `GET /health` (and `/`) returns real state -
version, provider, model, grounded rate, tool count, updater cycle, music node
and voice readiness - for the platform's health checks. The knowledge store
lives in `data/nexus.db` (SQLite, WAL), so a sleeping instance wakes up still
knowing what it verified and when it must re-check it. Mount a disk or sync the
file if you want memory to survive a rebuild.

Music needs a second Render service built from `deploy/lavalink/`. Keep its
`LAVALINK_PASSWORD` identical to the bot service, and point the bot's
`LAVALINK_URI` at that service. A Render free web service may sleep and is not
ideal for uninterrupted voice; use a continuously running instance for a
public music bot. See [`docs/MEDIA.md`](docs/MEDIA.md) for the exact fields.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q          # fully offline regression suite
```

`tests/conftest.py` blocks outbound HTTP and points the database at a temp file, so a red test means a **policy regression**, not a flaky API. Coverage: routing decisions, freshness classification, ranking and cross-check, the verifier's link/number/excuse rules, prompt assembly and budget, the knowledge store, cache staleness, the updater's confirm/correct/refuse policy, the API shape, Discord output safety.

---

## Project layout

```
ai/        engine, router, providers/, conversation manager, verifier, memory extractor,
           model catalog, provider manager, tool registry
search/    freshness policy, cache, ranking + cross-check, evidence report, query utils
tools/     one module per external source; TTLs, keywords, health, honest failures
core/      updater: the self-update cycle (runtime facts, probes, re-verify, maintenance)
database/  SQLite: profiles, memory, facts, verified knowledge + history, tool health
commands/  Discord cogs: chat, memory, admin, utility, music, live voice
media/     Lavalink helpers, voice buffering, Groq speech, Discord DAVE guard
prompts/   base · personality · creator · accuracy  (loaded per request)
api/       FastAPI surface over the same engine
utils/     settings, prompt loader, formatting, time, permissions, cooldowns, calculator
tests/     offline suite
deploy/    Lavalink v4 Docker service and pinned plugin configuration
docs/      ARCHITECTURE · ACCURACY · MEDIA · ROADMAP · SYSTEM_DESIGN · VISION
data/      the SQLite store (git-ignored)
```

Deeper: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (request path, layer rules,
failure model) · [`docs/ACCURACY.md`](docs/ACCURACY.md) (policy and knobs) ·
[`docs/MEDIA.md`](docs/MEDIA.md) (voice/music deployment) ·
[`docs/ROADMAP.md`](docs/ROADMAP.md) (what's next, in build order).

---

## Notes on honesty

- This README describes the code as it is. Placeholder tools are listed as placeholders. The image-generation endpoint is listed as unverified because it could not be verified from here.
- Retrieval quality is bounded by what a keyless bot may use. Add `BRAVE_API_KEY` or `GEMINI_API_KEY` for materially better coverage of "what happened today".
- Nexus verifies **against its sources**. If every result page repeats the same wrong number, it reports that number as corroborated - which is why disagreements are surfaced instead of averaged.
- The verifier judges links and numbers mechanically; it cannot tell whether an *explanation* is subtly wrong. Complex reasoning still needs a human.
- This sandbox had no model access, so the end-to-end pipeline has been exercised against stubbed providers and fixture evidence, not a live LLM. Run it once with a real key before trusting the numbers in a deploy.

---

Creator: **Izumi** (Rohit / IZ) · Special user: **Ash** (Ashey)

*Build once. Extend forever. Never assert what you cannot check.*
