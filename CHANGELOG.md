# Nexus Changelog

---

## Unreleased

### 🎧 Nexus 1.4.0-alpha.V4 media update

- Added a Lavalink v4 music system with 25 `/music` commands: connection,
  search/URL/playlist playback, queue editing, previous/replay, seek, loop,
  autoplay, volume, filters, interactive controls and per-guild cleanup.
- Added a separately deployable Lavalink image with pinned YouTube and LavaSrc
  plugins. Spotify URLs are resolved to a playable source; Spotify's API is not
  treated as an audio stream.
- Added opt-in `/voice` conversations using bounded Discord voice turns, Groq
  Whisper transcription, the normal Nexus accuracy engine and Groq Orpheus
  female speech. Raw audio is discarded after transcription.
- Added guarded inbound Discord DAVE compatibility for the pinned alpha voice
  receiver, controlled recovery after receiver failure, and media readiness in
  `/health`.
- Added clean per-guild handoff between music and live conversation because one
  Discord bot connection cannot run both modes in the same guild at once.
- Added an RMS voice-activity gate before Whisper, per-speaker transcript
  deduplication, bounded failure cleanup and rate-limited voice error notices.
- Groq TTS terms/permission failures now degrade to text without pausing STT;
  the same access warning is sent once per session state and later turns retry.
- Added authenticated Lavalink capability probing for LavaSrc, Spotify and the
  modern YouTube plugin, delayed Now Playing announcements, structured track
  exception logs, one-shot Spotify playback fallback, and retry deduplication.
- Added a shared per-guild audio coordinator so music and conversational voice
  cannot race while handing over Discord's single voice connection.
- Fixed Mistral startup detection for SDK builds that expose the client as
  `mistralai.client.Mistral` instead of a top-level export.

### 🐛 Fixed

- Spotify and YouTube search now remove request wording around a title without
  deleting title words, so requests such as “give me Love Me song link” query
  the APIs for `Love Me` instead of the whole sentence.
- Every retrieved URL now appears in one captioned link embed regardless of
  provider; Spotify links no longer depend on whether the language model chose
  to repeat them, and YouTube/Spotify artwork is attached to that embed.
- Discord requester attribution now includes display name, username and user ID.
- Explicit YouTube, Spotify, Reddit, GitHub, Steam, arXiv, and Stack Overflow
  lookups now route to real integrations before model generation.
- XML and bracketed `[TOOL_CALL]` text is rejected and can no longer leak into
  Discord replies.
- Spotify OAuth now uses a form body and reads the real plural search response
  containers (`tracks`, `albums`, `artists`).
- OpenRouter live search uses the hosted server-tool request shape and keeps
  the configured model fallback chain.
- Stack Overflow retrieves accepted or top-voted answers instead of labeling a
  question body as an accepted answer.
- Gemini calls run outside the event loop; ordinary answers no longer trigger
  an unrequested Google search.
- Aggregated tool calls now update health counters, activating the existing
  cooldown after repeated failures.
- arXiv PDFs remain links instead of invalid Discord images; DuckDuckGo,
  Spotify, and Steam artwork can now appear in reference embeds.
- Health and local API routes can start without an AI key and report an
  unconfigured provider; actual AI requests still return a configuration error.

### ✅ Tests

- Added offline regression coverage for YouTube, Spotify, Stack Overflow,
  OpenRouter search/fallbacks, direct routing, media images, and tool-call
  leakage.

### ✨ Added

- **Conditional Discord presentation** (`utils/rich_response.py`) - short and
  conversational answers remain normal messages. Detailed explanations and
  worked solutions use a plain introduction, one or more focused embeds, and a
  plain conclusion. The requester line remains outside the embed.
- **Reference images** - explanation embeds may show the first relevant HTTPS
  image supplied by retrieved evidence. Nexus never invents an image URL, and
  Wikipedia results now expose their page thumbnail when one exists.
- **Copy-friendly code delivery** - fenced code becomes syntax-labelled Discord
  embeds, multiple blocks become numbered parts, and oversized replacements are
  attached as complete files instead of being silently truncated.
- **Natural Discord conversations** - every DM works without a mention; tagged
  DMs still work; server messages work through either a mention or a direct
  reply to Nexus.
- **Complete environment templates** - `.env.example` now documents all 93
  supported settings once, including direct and local providers, search tools,
  accuracy controls, memory, file access, Render and logging.

### 🛠 Changed

- Merged the original Nexus identity rules with a clearer professional response
  contract in `prompts/base.txt`: lead with the answer, explain connections,
  use examples and limits where useful, fence generated code, and provide full
  files when a replacement is requested.
- Nexus now starts with Discord's idle presence and the activity
  `/ask  •  /music  •  /voice`.
- Explanations and solutions are more detailed without forcing simple chat into
  an embed or adding a decorative `Response` heading.

### 🐛 Fixed

- GNews now uses its current `/api/v4/search` endpoint and `apikey` parameter,
  correctly reads nested publisher metadata and images, and is still attempted
  when NewsAPI is configured but empty, unavailable or out of quota.
- Reddit is now OAuth-only: it remains unavailable until all approved
  credentials are configured, obtains and caches an application token, and no
  longer attempts unidentified public JSON requests.
- Missing Brave and LibreTranslate configuration now matches documented
  behaviour: Brave is simply skipped, while translation falls back to
  MyMemory.
- Code requests containing conversational words such as "now" no longer trigger
  unnecessary web searches or collide with weather, currency and other exact
  tools. Explicit requests for current APIs, releases or documentation still
  search normally.
- A provider refusal or plain-text failure can no longer be mislabeled as
  `Generated Implementation`; code presentation now requires fenced code or a
  recognisable code shape.
- OpenRouter tool-call markup can no longer leak directly into Discord when a
  model requests live search.
- Render health checks no longer crash during Discord startup when
  `bot.latency` is `NaN`; the endpoint returns JSON `null` until latency exists.
- DM prefix commands are no longer answered twice by both the command handler
  and the conversational message handler.

## Nexus 2.0.0-alpha.2
**Release Date:** 2026-09-03

The accuracy release. Nexus now decides *when* it is allowed to answer, checks
what it says against the evidence it collected, and re-verifies what it has
already learned instead of trusting it forever.

### ✨ Added

- **Request routing** (`ai/request_router.py`) - every message is classified
  before anything is spent on it: `instant` / `short` / `medium` / `long` /
  `static` freshness, exact-tool hits (weather, currency, clock, calculator,
  maps, translation), URL pastes, and a static-knowledge exemption so "why is
  the sky blue" never burns a search.
- **Freshness policy** (`search/freshness.py`) - one budget per question shape,
  respected identically by the cache, the ranker and the verifier.
- **Multi-source retrieval** (`search/aggregator.py`, `ranking.py`, `report.py`) -
  parallel tool fan-out under one deadline, authority + recency + relevance
  scoring, cross-domain corroboration that syndicated copies cannot fake,
  conflict detection, a `SearchReport` that carries its own verdict.
- **Freshness-aware cache** (`search/cache.py`) - stale-while-revalidate with a
  topic index, so a corrected fact does not keep being served from cache.
- **Verified-knowledge store** (`database/knowledge.py`) - grounded answers
  become durable rows with confidence, hit counts, expiry and full history;
  re-confirmation raises confidence, contradiction supersedes or marks the row
  `disputed`.
- **Answer verifier** (`ai/verifier.py`) - deletes citations no tool returned,
  caps answers whose figures are absent from the evidence, refuses to repeat
  "I cannot access the internet", forces one bounded repair pass, and discloses
  the residual uncertainty to the user.
- **Prompt assembly by priority** (`ai/conversation_manager.py`) - persona,
  evidence, verified notes, facts, memory; over-budget blocks are dropped whole,
  least important first, never mid-sentence.
- **Self-update loop** (`core/updater.py`) - refreshes runtime facts (version,
  provider, model, UTC + IST clock), probes every evidence tool with a real
  query, re-verifies knowledge past its shelf life, keeps hot topics warm,
  prunes weak rows. One cycle at a time; survives a free-tier sleep.
- **Model catalog** (`ai/model_catalog.py`) - re-reads provider `/models`,
  detects a retired model id and repairs the in-memory chain. `config.py` is
  never rewritten by the bot.
- **Provider robustness** (`ai/provider_manager.py`) - failure breakers with
  cooldown, capability-aware rotation, and no sticky provider mutation: a
  fallback answers once instead of silently repointing the bot.
- **20 tools, all honest about failure** (`tools/`) - each declares required
  keys, keywords, cache TTL and health; a tool that fails three times is
  removed from selection for 15 minutes; placeholder text can no longer reach
  the model as "evidence".
- **Slash commands** (`commands/`) - `/ask`, `/search`, `/sources`, `/verify`,
  `/remember`, `/forget`, `/facts`, `/version`, `/ping`, `/tools`, and the
  creator group `/nexus status|reverify|tools|models|accuracy|knowledge|provider|start-updating`.
- **Safe calculator** (`utils/calculator.py`) - restricted AST evaluation, so
  arithmetic is computed exactly and `1/0`, `__import__` and `2**5000` are
  refused instead of executed.
- **Permissions and cooldowns** (`utils/permissions.py`, `utils/cooldown.py`) -
  creator / special / admin / user roles in one place, and quota protection so
  one chatty user cannot spend the provider's rate limit for the server.
- **Docs** - `docs/ARCHITECTURE.md`, `docs/ACCURACY.md`, `docs/ROADMAP.md`,
  expanded `.env.example`, and a test suite that runs offline
  (`tests/`, 100 assertions, network blocked by `conftest`).

### 🛠 Changed

- `prompts/base.txt` and the new `prompts/accuracy.txt` are enforced by code,
  not just requested: the runtime block states the real clock, version, active
  provider/model and which tools are answering right now.
- Database is versioned (`SCHEMA_VERSION=3`) and migrates in place with WAL mode,
  so a deployed bot gains the accuracy columns without an operator running SQL.
- `bot.py` loads cogs dynamically, syncs the command tree (optionally to one
  guild via `COMMAND_GUILD_ID`), answers DMs, and serves a real `/health`
  payload: grounded rate, tool count, updater cycle state.
- API routes now return grounding metadata (`grounded`, `confidence`, `verdict`,
  citations) instead of an unlabelled list of strings.

### 🐛 Fixed

- `api/routes/memory.py` imported a function that did not exist (`load_memory`),
  which made the whole FastAPI app unimportable.
- `api/routes/{search,research}.py` assumed the aggregator returned plain dicts.
- The provider manager reassigned `self.provider` on every fallback.
- The router treated bare acknowledgements ("ok", "thanks!") as questions and
  searched for them.
- Currency and clock questions fell through to an unsearched model guess;
  "what time is it in Tokyo" was classified as timeless knowledge.
- `tools/reddit.py` did not parse; `tools/news.py` and `tools/google_search.py`
  had broken imports/regexes; several tools could not survive an empty response.

### 🎯 Next

- Vision input for attachments, per-tool timeouts, a labelled retrieval eval set,
  and `/nexus history` to show the bot correcting itself.

## Nexus 2.0.0-alpha.1
**Release Date:** 2026-07-07

### 🚀 Project Started

The beginning of Project Nexus.

### ✨ Added

- Created the new modular project architecture.
- Added AI engine folder.
- Added AI provider system.
- Added command modules.
- Added database modules.
- Added prompts folder.
- Added utility modules.
- Added backup system.
- Added documentation folder.
- Added testing folder.
- Added project versioning.

### 🛠 Changed

- Separated development into the `Nexus-V2` branch.
- Began complete rewrite from Nexus v1.

### 🎯 Next Goals

- Build the AI Engine.
- Implement provider management.
- Create Discord slash commands.
- Implement permissions.
- Create the memory system.
