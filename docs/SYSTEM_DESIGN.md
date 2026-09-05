# 🌌 Project Nexus — System Design

**Version:** Nexus 1.4.0-alpha.V4
**Status:** implementation reference for the `Nexus-V3` branch

---

## Purpose

Project Nexus is a modular Discord AI assistant. A language model is only one
replaceable part: Nexus decides when evidence is needed, retrieves it, verifies
the draft, stores only supported knowledge, and presents the result for Discord.

The system keeps working when an optional provider, API key, or evidence tool
is unavailable. Missing capabilities are reported, not replaced with invented
output.

---

## End-to-end request flow

```text
Discord DM / mention / reply / command
                    │
                    ▼
                bot.py
                    │
                    ▼
          ai/request_router.py
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       local       chat      search
                               │
                               ▼
                    search/aggregator.py
                    cache · ranking · cross-check
                               │
                               ▼
                 ai/conversation_manager.py
                 persona · evidence · memory
                               │
                               ▼
                   ai/provider_manager.py
                   provider/model failover
                               │
                               ▼
                       ai/verifier.py
                  links · figures · grounding
                               │
                               ▼
                  utils/rich_response.py
                plain · reference · solution · code
                               │
                               ▼
                         Discord output
```

`ai/engine.py` owns orchestration. Discord commands and the HTTP API both call
the same engine, so they cannot develop different accuracy rules.

---

## Discord ingress

`bot.py` is wiring, not AI policy.

- A direct message is a one-to-one conversation; no mention is required,
  although a tagged DM still works.
- In a server, Nexus answers when mentioned or when a user directly replies to
  one of Nexus' messages.
- Slash commands and valid prefix commands are handled exactly once.
- Up to three attachment URLs are forwarded as context. Unsupported image
  understanding is disclosed rather than simulated.
- Nexus starts idle with the activity `/ask  •  /music  •  /voice`.
- `/` and `/health` expose deploy state for Render. Discord latency is `null`
  during startup if the client has not produced a finite value yet.

---

## Request routing

`ai/request_router.py` classifies every request before a provider is called.

| Route | Used for | Behaviour |
|---|---|---|
| `local` | acknowledgements and empty input | no provider or search cost |
| `chat` | greetings, stable knowledge, ordinary code generation | answer from the configured model |
| `search` | current claims, explicit lookup, substantial reference topics, exact tools | retrieve evidence before generation |

Freshness classes (`instant`, `short`, `medium`, `long`, `static`) determine
cache and verification limits. Exact tools handle arithmetic, weather,
currency, time, maps and translation where specialised data is safer than model
recall.

Code generation is protected from keyword collisions. “Now write a weather
bot” is static code work, not a current-weather lookup. Code searches only when
the user explicitly asks to search or requests current APIs, versions, releases
or documentation.

The route also carries a presentation hint: `plain` for normal conversation,
`reference` for substantial explanations, and `solution` for worked maths and
similar tasks. Code is confirmed later from fenced or recognisably executable
output.

---

## Evidence and verification

`search/aggregator.py` runs selected tools concurrently under one deadline. It
removes empty or placeholder results, applies authority, relevance and recency
scores, deduplicates syndicated copies, and checks independent-domain agreement.

`ai/verifier.py` compares the generated draft with that evidence:

1. URLs that no tool returned are removed.
2. Unsupported numbers reduce confidence and may trigger one repair pass.
3. False “I cannot browse” claims are removed when Nexus retrieved evidence.
4. Current questions without adequate support are retried once, then hedged or
   refused according to configuration.
5. Residual uncertainty is shown to the user.

Only grounded public claims enter the knowledge store. Corrections retain
history; unresolved contradictions become `disputed` rather than averaged.

See [ACCURACY.md](ACCURACY.md) for policy and environment controls.

---

## Provider system

Every provider implements `ai/providers/base.py`. The provider manager selects
an available adapter, applies capability requirements, and uses a failure
breaker so an unhealthy provider cools down while the next option is attempted.

Supported adapters: OpenRouter, OpenAI, Gemini, Claude, Groq, DeepSeek,
Mistral, Cohere, Ollama and LM Studio.

OpenRouter may use a comma-separated model chain. Models run left to right;
`openrouter/free` can be the final router-managed fallback. The model catalog
may repair a retired ID for the current process, but Nexus never rewrites
`config.py` or `.env`.

All provider, model and tool settings are documented in
[`../.env.example`](../.env.example).

---

## Prompt and conversation assembly

`ai/conversation_manager.py` loads prompt blocks in priority order:

1. `prompts/base.txt` — Project Nexus identity and response contract;
2. `prompts/personality.txt` — conversational style;
3. `prompts/creator.txt` — stable project identity facts;
4. `prompts/accuracy.txt` — evidence and uncertainty rules;
5. live runtime facts — clock, version, provider, model and tool inventory;
6. retrieved evidence and verified knowledge;
7. relevant user facts and recent conversation.

Lower-priority blocks are removed whole when the context budget is exceeded.
The system does not cut a policy block or evidence item in half.

The response contract requires professional, readable answers: lead with the
answer, explain important connections, include examples and meaningful limits
for complex topics, and avoid decorative headings such as `Response`.
Replacement-file requests return complete files, and code uses fenced blocks
with the correct language.

---

## Discord presentation

`utils/rich_response.py` formats a verified outcome without changing its facts.

| Kind | Output |
|---|---|
| Plain | normal Discord text |
| Reference | plain introduction → focused embed → plain conclusion |
| Solution | plain setup → worked-solution embed → plain explanation |
| Code | plain introduction → syntax-labelled code embeds → plain conclusion |

The requester line is compact normal Discord text, not an embed. Long code is
previewed and attached as a complete replacement file. A refusal is never
labelled as generated code merely because the question asked for code.

Reference images are optional. Nexus uses only an HTTPS image or thumbnail
returned by retrieval; it does not trust a URL invented in model text. Normal
conversation never receives an embed merely for decoration.

---

## Music and live voice

Media is an optional layer beside text chat; it does not change the accuracy
pipeline or prevent the bot from starting when media credentials are absent.

Music uses `commands/music.py`, Wavelink and a separate Lavalink v4 process.
Each guild has its own queue, playback lock and control state. Search terms,
direct URLs and playlists resolve on Lavalink; the YouTube and LavaSrc plugins
provide YouTube search and Spotify-to-playable-source matching. The bot releases
the player when the channel becomes empty or its inactivity timer expires.

Live voice uses `commands/voice.py` and `media/`:

```text
Discord decoded PCM → bounded turn buffer → Groq Whisper STT
                    → ai/engine.py → Groq Orpheus TTS → Discord playback
```

This is turn-based, near-real-time conversation, not simultaneous full duplex.
The session ignores bot audio while Nexus speaks, discards PCM after
transcription, and sends the resulting text through the normal Nexus
conversation-memory policy. Posting a text mirror is independently configurable.
Starting a session requires a consent confirmation. A compatibility guard
supplies inbound DAVE decryption for the pinned alpha voice-receive extension
and refuses to start if the expected Discord voice stack is unavailable.

Discord supports one bot voice connection per guild. Starting music stops live
conversation in that guild and starting live conversation disconnects music;
other guilds are unaffected. See [MEDIA.md](MEDIA.md) for deployment and the
complete command list.

---

## Persistence

Nexus uses one SQLite database in WAL mode. Startup migrations are additive.

| Table | Responsibility |
|---|---|
| `profiles` | identity, preferences and usage metadata |
| `messages` | bounded recent conversation |
| `facts` | durable user facts with provenance and supersession |
| `knowledge` | verified public claims, confidence, expiry and status |
| `knowledge_history` | prior values and correction reasons |
| `tool_health` | source probes, errors and cooldown state |
| `settings` | runtime settings that must survive restart |

Users can inspect or erase remembered information through `/facts`, `/forget`
and the matching API route.

---

## Background self-update

`core/updater.py` runs one locked asynchronous cycle:

1. refresh runtime facts;
2. probe evidence tools;
3. re-check expired knowledge;
4. refresh frequently requested topics;
5. prune expired cache and weak knowledge;
6. refresh provider model catalogs.

This is knowledge maintenance, not self-modifying code. It never rewrites source
files or secrets.

---

## Failure behaviour

| Failure | Expected behaviour |
|---|---|
| Provider missing or rate-limited | try the next capable provider; retain configured default |
| Evidence tool unavailable | skip it, record health, disclose reduced evidence |
| Search deadline reached | use labelled partial evidence or refuse according to policy |
| Current claim cannot be verified | one bounded retry, then an honest caveat/refusal |
| Fabricated citation | remove it before Discord output |
| Raw provider tool-call envelope | execute or normalise it; never post raw markup |
| Oversized code | attach the complete file |
| Startup latency is `NaN` | return `null` from health endpoint, not HTTP 500 |
| Lavalink is absent or unhealthy | keep AI chat online; `/music status` reports exact setup/connection state |
| Music channel becomes empty | disconnect and release queue/player resources |
| STT/TTS key or FFmpeg is absent | keep text and music online; `/voice status` reports the missing dependency |
| Voice receive fails mid-session | restart the listener once when safe; otherwise close only that guild session |
| Voice protocol shape is incompatible | refuse live receive instead of processing undecrypted/corrupt audio |
| Updater cycle fails | log and end that cycle; chat remains available |

---

## Security boundaries

- External text is prompt-framed as untrusted evidence.
- Output neutralises mass mentions.
- File reading is opt-in and confined to `FILE_READER_ROOT`.
- Arithmetic uses a restricted AST evaluator, never `eval`.
- Secrets come from environment variables and must not be committed.
- Placeholder OCR, vision and image-generation tools report unavailable rather
  than pretending to work.

---

## Development rules

- Keep provider-specific HTTP details inside `ai/providers/`.
- Keep retrieval policy outside Discord cogs.
- Keep presentation separate from verification.
- Add a regression test for every routing, safety or formatting bug.
- Preserve working features while replacing only the failing layer.
- Update this document, [ARCHITECTURE.md](ARCHITECTURE.md),
  [ACCURACY.md](ACCURACY.md), and [ROADMAP.md](ROADMAP.md) when behaviour changes.

Project Nexus should expand without discarding its working foundation: build
once, verify continuously, and extend deliberately.
