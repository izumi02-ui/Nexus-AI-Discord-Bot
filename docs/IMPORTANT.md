# IMPORTANT.md — Project Nexus / Nexy Master Status

> **Repository:** `izumi02-ui/Nexus-AI-Discord-Bot`
> **Branch:** `Nexus-V4`
> **Current generation:** `Nexus 1.4.0-alpha.V4`
> **Purpose:** single source of truth for what Nexus is, what it can do now, what is partial, what is broken, what is infrastructure-only, and what must not be casually rewritten.

---

## Status legend

| Mark | Meaning |
|---|---|
| ✅ | Implemented / working in current architecture |
| 🟡 | Implemented but incomplete, provider-dependent, or needs hardening |
| 🔴 | Known production problem / unreliable |
| 🛠️ | Infrastructure or deployment requirement |
| 🧪 | Experimental / compatibility workaround |
| ⏳ | Planned / not production-ready |
| 🚫 | Explicitly avoid |

---

# 1. What Nexus is

Nexus/Nexy is not only a Discord chatbot. It is an AI system built around a provider-independent pipeline whose job is to reduce guessing and verify claims before presenting them as trustworthy.

```text
route → recall → retrieve → compose → answer → verify → learn
```

Core rule:

> The model is replaceable. Nexus itself is the routing, retrieval, verification, memory, tools, presentation, media, API, and reliability layer around the model.

Current major systems:

```text
bot.py
ai/
api/
commands/
core/
database/
deploy/
docs/
media/
prompts/
search/
tests/
tools/
utils/
```

Do not collapse these layers into one giant bot file.

---

# 2. Current architecture

```text
Discord / HTTP request
        │
        ▼
   bot.py / api/
        │
        ▼
    ai/engine.py
        │
        ├── request routing
        ├── verified knowledge recall
        ├── search / evidence gathering
        ├── conversation / prompt assembly
        ├── provider selection + failover
        ├── verification
        └── learning / persistence
```

| Layer | Owns | Must not become |
|---|---|---|
| `bot.py` | Discord ingress, cogs, health server | AI policy |
| `commands/` | UX, commands, permissions, cooldowns | provider logic |
| `ai/` | orchestration, providers, prompts, verification | Discord UI |
| `search/` | freshness, cache, ranking, reports | Discord-aware logic |
| `tools/` | external evidence sources | fake-success placeholders |
| `database/` | memory, profiles, knowledge, history | business-logic dump |
| `core/` | updater/self-maintenance | config mutator |
| `media/` | music/voice helpers, DAVE compatibility | raw audio persistence |
| `utils/` | settings, permissions, formatting | accuracy policy |
| `api/` | HTTP surface over Nexus | second AI implementation |

---

# 3. AI core

Status: ✅

Current capabilities:

- natural-language conversation
- route whether a query needs fresh retrieval
- freshness classification
- verified knowledge recall
- multi-source retrieval
- ranking and deduplication
- conflict detection
- prompt assembly from persona, evidence, facts and memory
- provider fallback
- post-generation verification
- one bounded repair pass
- learning/persistence of verified knowledge
- grounding metadata

---

# 4. Provider system

Status: ✅ / 🟡 depending on keys/provider availability.

Current provider modules include:

```text
OpenRouter
OpenAI
Gemini
Claude
Groq
DeepSeek
Mistral
Cohere
Ollama
LM Studio
```

Architecture rules:

- provider is a plug, not the whole product
- failure breaker/cooldown behavior exists
- fallback should move to the next capable provider
- model catalogue can repair retired model IDs at runtime
- committed configuration must not be silently rewritten
- new providers must inherit Nexus verification instead of bypassing it

Relevant files:

```text
ai/provider_manager.py
ai/provider_capabilities.py
ai/model_catalog.py
ai/providers/*
```

---

# 5. Accuracy / verification

Status: ✅

Implemented concepts:

- freshness policy
- authority/recency ranking
- cross-domain corroboration
- conflict detection
- fabricated-citation removal
- evidence-aware numeric confidence
- one bounded repair pass
- uncertainty disclosure
- verified knowledge storage
- knowledge history
- disputed state

Freshness classes include:

```text
instant
short
medium
long
static
```

Nexus should prefer “could not verify” over inventing a confident answer.

---

# 6. Search / research / tools

Status: ✅ / 🟡 depending on key/source health.

Current tool areas include:

```text
arxiv
brave
calculator
currency
duckduckgo
file_reader
github
google_search
maps
news
ocr
reddit
spotify
stackoverflow
steam
time
translator
vision
weather
web_scraper
web_search
wikipedia
youtube
```

Tool behavior:

- tool-level health state
- TTL/freshness
- keyword routing
- required-key reporting
- cooldown after repeated failures
- one failed tool must not kill chat

Known incomplete areas:

- vision/image understanding ⏳
- OCR production readiness ⏳
- image generation ⏳

---

# 7. Memory / knowledge

Status: ✅

Current concepts:

- rolling per-user conversation memory
- durable personal facts
- provenance/history
- `/remember`
- `/forget`
- `/facts`
- verified public knowledge
- expiry/staleness
- change history
- superseding old facts instead of blind duplication

Relevant files:

```text
database/memory.py
database/fact_manager.py
database/knowledge.py
database/profile_manager.py
database/user_profile.py
ai/memory_extractor.py
ai/conversation_manager.py
```

Memory must remain user-auditable.

---

# 8. Self-updating system

Status: ✅ / 🟡 provider/tool dependent.

`core/updater.py` is intended to:

- refresh runtime facts
- probe tools
- re-verify stale knowledge
- keep frequently requested topics warm
- prune weak/expired data
- refresh provider model catalogues
- repair retired model IDs for the running session

Rules:

- updater failure must not kill chat
- one cycle at a time
- bounded work
- do not rewrite committed config

---

# 9. Discord capabilities

Status: ✅

Current behavior includes:

- slash commands
- prefix commands
- normal DM conversation
- server mention/reply conversation
- cog auto-loading
- idle presence
- cooldown support
- attachment recognition
- health endpoint
- separate admin/chat/memory/music/utility/voice cogs

Important command families include:

```text
/ask
/search
/sources
/verify
/remember
/forget
/facts
/tools
/version
/ping
/nexus ...
/music ...
/voice ...
```

---

# 10. Rich responses

Status: ✅

Current system supports:

- plain replies for normal chat
- structured embeds for substantial explanations
- grounding/source metadata
- retrieved reference images only when a source supplies one
- code blocks
- long-code file fallback
- Discord-safe splitting
- `@everyone` neutralisation

Relevant file:

```text
utils/rich_response.py
```

Do not replace this with “everything is an embed” unless explicitly requested.

---

# 11. FastAPI / Nexus API

Status: ✅ foundation / 🟡 auth incomplete.

Current API structure includes:

```text
api/app.py
api/routes/chat.py
api/routes/health.py
api/routes/memory.py
api/routes/models.py
api/routes/research.py
api/routes/search.py
api/routes/tools.py
api/middleware/
api/schemas/
```

Rule:

> Web/mobile must call the same Nexus brain. Do not make a separate JavaScript AI implementation.

Known gap:

- production authentication/authorization is not complete
- some middleware/schema files are minimal/placeholders
- future app auth must be real, server-side and verified

---

# 12. Music system

Status: 🟡 architecture implemented, 🔴 production reliability issues remain.

## Current architecture

```text
/music
  ↓
commands/music.py
  ↓
Wavelink
  ↓
Lavalink v4
  ├── youtube-source
  └── LavaSrc
      ├── Spotify metadata
      └── playable-source resolution
```

Implemented features include:

```text
join
play
playnext
pause
resume
skip
previous
replay
stop
disconnect
queue
nowplaying
remove
move
jump
shuffle
clear
loop
volume
seek
autoplay
filter
status
help
```

Also:

- per-guild queues
- interactive controls
- automatic cleanup
- shared audio ownership with live voice

---

# 13. Lavalink connection problem

Status: 🔴 / 🛠️

Observed production status:

```text
feature: enabled
Lavalink: not connected
node: nexus-main · 0 configured
active players: 0
LavaSrc: not confirmed
Spotify resolution: not confirmed
modern YouTube plugin: not confirmed
YouTube source: not confirmed
```

Observed `/music play`:

```text
The Lavalink node is reconnecting. Try again in a moment.
```

Known infrastructure discovery:

- Railway Lavalink deployment was found `SLEEPING`
- Serverless must be OFF for Lavalink
- sleeping Lavalink is an infrastructure state, not a reason to rewrite music

Expected env:

```text
MUSIC_ENABLED=true
LAVALINK_URI=<Railway Lavalink endpoint>
LAVALINK_PASSWORD=<same secret used by Lavalink>
```

Never hardcode domain/password.

Code hardening still required:

- bot must start without Lavalink
- temporary node failure must not strand music forever
- bounded reconnect/backoff
- reconnect when node becomes available
- refresh capabilities after reconnect
- no retry storms
- `/music status` should distinguish disconnected / connecting / reconnecting / connected / probe-failed

---

# 14. YouTube music problem

Status: 🔴 external-source reliability issue.

Observed Lavalink failures have included:

```text
Sign in to confirm you're not a bot
403
stream extraction failures
AllClientsFailedException
```

Likely cause:

- YouTube frequently restricts datacenter/cloud-hosted IPs

Rule:

🚫 Do not design Nexus music around “YouTube always works”.

---

# 15. Spotify/LavaSrc problem

Status: 🔴 external/API restriction issue.

Observed:

- Spotify metadata/API requests have returned HTTP 403

Stable intended direction:

```text
plain search
  ↓
SoundCloud first
  ↓
YouTube fallback

Spotify track URL
  ↓
Spotify metadata
  ↓
SoundCloud playable mirror first
  ↓
YouTube last fallback
```

For a single Spotify track, a public metadata fallback such as Spotify oEmbed may be used where appropriate if official metadata access is blocked.

Spotify album/playlist failures must return accurate user-facing errors instead of fake “no tracks”.

---

# 16. Lavalink config

Current intended architecture:

```text
youtube-plugin 1.18.2
LavaSrc 4.8.3
built-in YouTube source disabled
modern YouTube plugin enabled
SoundCloud enabled
Spotify enabled
```

Provider order is roughly:

```text
scsearch:%QUERY%
ytsearch:"%ISRC%"
ytsearch:%QUERY%
```

Important:

`commands/music.py` performs direct Wavelink searches in some paths.

Do not assume LavaSrc provider ordering automatically makes every plain-text bot search SoundCloud-first.

---

# 17. Live voice

Status: 🟡 implemented, 🔴 receive reliability issue remains.

Current voice path:

```text
Discord PCM
  ↓
voice receive
  ↓
noise/activity gate
  ↓
turn segmentation
  ↓
Groq Whisper STT
  ↓
existing Nexus engine
  ↓
Groq Orpheus TTS
  ↓
Discord voice output
```

Implemented commands:

```text
/voice join
/voice start
/voice mute
/voice unmute
/voice say
/voice status
/voice stop
/voice leave
```

Implemented protections:

- bounded in-memory audio buffer
- no intentional raw-audio DB persistence
- duplicate transcript protection
- silence/noise RMS gate
- optional text mirror
- transcribed text uses normal Nexus memory policy
- music ↔ voice handoff

---

# 18. Voice receive failure

Status: 🔴

Observed:

```text
Nexy is listening
```

then:

```text
Live listening stopped because Discord voice receive could not recover.
Use /voice start to open a fresh session.
```

Current recovery is too fragile because it effectively allows only one controlled restart before session closure.

Required behavior:

- bounded multiple recovery attempts
- increasing backoff
- reset recovery counter after healthy period
- no duplicate sinks/listeners
- clean cancellation on leave
- mute/unmute race safety
- no recovery/shutdown race
- reconnect underlying voice client if the current receive client is corrupted
- close only after real bounded failure

---

# 19. DAVE / Discord E2EE compatibility

Status: 🧪 / 🔴 fragile dependency area.

Current dependencies include approximately:

```text
discord.py[voice]>=2.7.1,<3
davey>=0.1.6,<0.2
discord-ext-voice-recv==0.5.2a179
```

Custom compatibility file:

```text
media/dave_compat.py
```

Rules:

- do not blindly remove DAVE
- patch must stay idempotent
- prefer native upstream compatibility when available
- a bad individual frame should not kill the receive worker
- persistent protocol failure must not be swallowed forever
- do not blindly upgrade pinned voice dependencies

---

# 20. STT

Status: ✅ has worked.

Current intended model:

```text
Groq
whisper-large-v3-turbo
```

STT should remain usable even when TTS is unavailable.

---

# 21. TTS

Status: 🟡 configured, 🔴 provider-access issue observed.

Current intended config:

```text
provider: Groq
model: canopylabs/orpheus-v1-english
voice: hannah
```

Observed:

- HTTP 403
- model access / model terms required

Important:

- a new API key from the same org/project does not necessarily change model entitlement
- TTS failure must not kill STT/listening
- use text fallback
- suppress repeated identical access-denied notices

Status must distinguish:

```text
configured
unverified
verified
access denied
```

Do not call TTS “ready” merely because an API key exists.

---

# 22. Audio ownership

Status: ✅ architecture / 🟡 reliability testing required.

Relevant file:

```text
media/audio_coordinator.py
```

One Nexus audio mode per guild.

Required transitions:

```text
music → voice
voice → music
voice failure → release
music disconnect → release
unexpected Discord disconnect → cleanup
```

Never create two simultaneous Discord voice clients for one guild.

---

# 23. Current database

Status: ✅ for current bot scale / 🟡 not final consumer-app DB.

Current storage:

```text
SQLite
data/nexus.db
WAL mode
startup migrations
```

Current concepts:

```text
profiles
messages
facts
knowledge
knowledge_history
tool_health
settings
```

Future multi-user product:

- migrate deliberately to PostgreSQL or another transactional DB
- preserve existing memory through migrations
- Google Drive is backup/export/file integration only
- 🚫 do not use Google Drive as primary auth/chat/subscription database

---

# 24. Hosting / deployment history

Status: 🛠️

## Render

Observed:

- Discord/Cloudflare access problems
- Error 1015 / datacenter IP temporary block behavior

This was not simply a Python syntax failure.

Current decision:

- do not move the bot back to Render as the automatic fix

## Railway

Current direction:

```text
Bot → Railway
Lavalink → Railway
```

Observed:

- GitHub-source deployment failed before build start
- reconnecting GitHub did not resolve it
- Railway CLI upload path worked
- free-tier SFO/US-West deploy was blocked during peak-hours policy
- free plan may lock region
- Serverless must be OFF for persistent bot/Lavalink

Lavalink public networking targets:

```text
port 2333
```

---

# 25. Security warning

Status: 🔴 review required.

Current repo tree contains:

```text
env.zip
```

Treat this as a potential secret leak immediately.

Required action:

1. inspect whether it contains credentials without printing them
2. if credentials were committed:
   - remove the artifact
   - rotate affected credentials
   - update `.gitignore`
   - consider Git history cleanup
3. never ship secrets to frontend
4. never log API keys, tokens, Lavalink passwords, OAuth tokens, OTPs or signing credentials

---

# 26. Tests

Status: ✅ broad test foundation exists.

Current suite includes areas such as:

```text
test_api.py
test_cache.py
test_calculator.py
test_conversation.py
test_discord_output.py
test_freshness.py
test_knowledge.py
test_media.py
test_openrouter.py
test_prompt.py
test_ranking.py
test_rich_response.py
test_router.py
test_tools.py
test_updater.py
test_verifier.py
test_voice_music_reliability.py
```

Music/voice fixes must verify:

- startup without Lavalink
- reconnect lifecycle
- no retry storm
- SoundCloud-first resolution
- bounded fallback
- one voice receiver per guild
- receiver recovery
- leave during recovery
- mute/unmute safety
- TTS denial while STT stays alive
- audio coordinator cleanup

---

# 27. Capability matrix

| System | Capability | Status |
|---|---|---|
| AI | Natural-language chat | ✅ |
| AI | Provider swapping | ✅ |
| AI | Provider failover | ✅ |
| AI | Model catalogue refresh | ✅ |
| Accuracy | Freshness routing | ✅ |
| Accuracy | Multi-source retrieval | ✅ |
| Accuracy | Evidence ranking | ✅ |
| Accuracy | Conflict detection | ✅ |
| Accuracy | Post-generation verification | ✅ |
| Accuracy | Bounded repair pass | ✅ |
| Memory | Rolling conversation memory | ✅ |
| Memory | Durable facts | ✅ |
| Memory | Forget/audit controls | ✅ |
| Knowledge | Verified knowledge store | ✅ |
| Knowledge | Expiry/stale handling | ✅ |
| Knowledge | Change history | ✅ |
| Search | Multiple evidence tools | ✅ / 🟡 |
| Tools | Health/cooldown | ✅ |
| Discord | Slash commands | ✅ |
| Discord | Prefix commands | ✅ |
| Discord | DM chat | ✅ |
| Discord | Mention/reply chat | ✅ |
| Discord | Rich responses | ✅ |
| Discord | Code/file output | ✅ |
| API | Chat | ✅ |
| API | Search | ✅ |
| API | Research | ✅ |
| API | Memory | ✅ |
| API | Models/tools/health | ✅ |
| API | Production auth | ⏳ |
| Music | Lavalink architecture | ✅ |
| Music | Queue/controls | ✅ |
| Music | Lavalink uptime/reconnect | 🔴 |
| Music | YouTube reliability | 🔴 external |
| Music | Spotify metadata reliability | 🔴 external |
| Music | SoundCloud-first resolver | 🟡 |
| Voice | Join/listen architecture | ✅ |
| Voice | Groq STT | ✅ |
| Voice | Groq TTS | 🟡 / 🔴 |
| Voice | DAVE compatibility | 🧪 |
| Voice | Long-lived receive stability | 🔴 |
| Media | Music/voice ownership | ✅ / 🟡 |
| Updater | Background re-verification | ✅ |
| Hosting | Railway deployment | 🟡 |
| Security | Secrets management | 🟡 |
| Security | `env.zip` audit | 🔴 |
| Vision | Image understanding | ⏳ |
| OCR | Production OCR | ⏳ |
| Images | Image generation | ⏳ |
| Web app | Nexus web UI | ⏳ |
| Android | Nexus Android app | ⏳ |
| Payments | Membership | ⏳ |
| Admin | Full product admin panel | ⏳ |

---

# 28. What must not be randomly rewritten

Do not casually rewrite:

```text
ai/engine.py
ai/provider_manager.py
ai/request_router.py
ai/verifier.py
search/*
database/*
utils/rich_response.py
media/audio_coordinator.py
prompts/*
```

Do not:

- replace provider-independent architecture with a single-provider bot
- hardcode secrets/domains/user IDs
- create permanent monkey-patch cogs for fixes that belong in existing modules
- bypass verifier for new providers
- make media failure prevent text AI startup
- assume infrastructure failures are application bugs
- assume providers/APIs are always available
- introduce infinite reconnect loops
- introduce two voice clients per guild

---

# 29. Current production priority order

## P0 — Security

```text
audit env.zip
rotate leaked credentials if any
ensure secrets stay out of Git
```

## P1 — Music connection reliability

```text
Serverless OFF
Lavalink stays awake
bot reconnects after node recovery
status shows real connection state
```

## P2 — Music source reliability

```text
plain search → SoundCloud first
Spotify track metadata → SoundCloud mirror first
YouTube → fallback only
bounded + deduplicated fallback
```

## P3 — Voice receive stability

```text
bounded recovery
backoff
single-listener guarantee
voice-client reconnect if necessary
safe shutdown/mute/unmute
```

## P4 — TTS runtime-state handling

```text
configured ≠ verified
keep STT alive on TTS denial
text fallback
no repeated error spam
```

## P5 — Railway production hardening

```text
persistent services
Serverless OFF
stable deploy path
health checks
environment validation
```

---

# 30. Validation before claiming media is fixed

1. compile/import changed Python modules
2. run relevant tests
3. confirm bot boots without Lavalink
4. simulate Lavalink unavailable → available
5. verify reconnect
6. refresh node capabilities after reconnect
7. verify `/music status`
8. verify plain-text search is SoundCloud-first
9. prove fallback cannot recurse forever
10. verify Spotify failure returns accurate error
11. verify `/voice start` creates one receiver
12. simulate receiver failure
13. verify bounded recovery
14. verify `/voice leave` cancels recovery
15. verify mute/unmute cannot duplicate listeners
16. verify TTS denial leaves STT/listening alive
17. verify audio ownership release
18. verify logs contain no secrets

---

# 31. Future Nexus product direction

Status: ⏳

Nexus is intended to expand beyond Discord into:

```text
Nexus Web
Nexus PWA
Nexus Android app
future Play Store release
official Nexus download website
chat history
images
library
projects
scheduled tasks
profile
settings
real authentication
membership/subscriptions
admin panel
```

Current planned UI exclusions:

```text
Remote
Plugins
```

The future app must reuse the existing Nexus backend/AI engine.

Do not rebuild Nexus as a disconnected frontend-only AI system.

---

# 32. Future authentication

Status: ⏳

Desired real authentication:

```text
email + password
email OTP
phone OTP
GitHub OAuth
```

Requirements:

- verified identities
- OTP expiry
- one-time OTP use
- resend cooldown
- rate limiting
- secure password hashing
- secure sessions
- session revocation
- account linking
- server-side authorization
- protected admin role
- no privileged long-lived secrets in browser storage

---

# 33. Future database direction

Status: ⏳

Preferred primary database for the full web/mobile product:

```text
PostgreSQL
```

Possible managed providers:

```text
Railway Postgres
Supabase Postgres
Neon
```

Google Drive may be used for:

```text
backup
export/import
optional user file copies
archive storage
```

🚫 Google Drive is not the transactional primary DB for users, OTPs, sessions, chats, subscriptions or admin state.

---

# 34. Future UI direction

Status: ⏳

Desired Nexus identity:

```text
dark
cinematic
premium
futuristic
mobile-first
Android-optimized
liquid-glass accents
liquid-metal Nexus logo
smooth motion
```

Requested references for future UI work:

```text
Framer Motion
ui-ux-pro-max-skill
liquid-glass-js
liquid-logo / @paper-design/shaders-react
```

Rules:

- reference, do not pixel-clone another product
- Android performance first
- respect reduced motion
- heavy shaders must be optional/lazy
- cinematic launch animation should be short and non-blocking
- official website should provide direct signed Android download
- future Play Store release must follow current store/billing requirements

---

# 35. Master rule for any coding agent

Before changing Nexus:

```text
READ THE CURRENT Nexus-V4 IMPLEMENTATION FIRST.
```

Then:

- decide whether the issue is code, provider, Discord, Lavalink, Railway, or external-source related
- make the smallest clean fix
- preserve architecture
- preserve UX unless a change is necessary
- add/update tests
- report changed files
- report root cause
- report remaining infrastructure work
- never claim success without inspecting/testing the actual path

---

# 36. One-line current summary

```text
Nexus-V4 already has a serious AI core, retrieval/verification pipeline,
multi-provider routing, memory, verified knowledge, tools, FastAPI,
Discord UX, Lavalink music architecture, and Groq live-voice architecture.

The largest current blockers are:
1. Lavalink persistence/reconnect,
2. unreliable YouTube/Spotify cloud-source playback,
3. Discord voice receive/DAVE stability,
4. Groq TTS entitlement/runtime-state handling,
5. Railway deployment/persistence constraints,
6. repository secret hygiene around env.zip.

Future Nexus Web/Android work should be built around this core, not replace it.
```
