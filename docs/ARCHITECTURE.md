# 🌌 Project Nexus — Architecture

**Version:** Nexus 1.4.0-alpha.V4
**Doc status:** describes the code in this repository, not an aspiration.

---

# The one idea

A language model is a confident guesser. Nexus wraps that guesser in a pipeline
that decides **what it is allowed to know**, then checks **what it is allowed to
say**, then remembers what it proved.

Everything in `ai/`, `search/` and `core/` exists to serve that sentence.

---

# Request path

```
Discord message
      │
      ▼
bot.py ──────────────── intents, cog loading, health server, updater start
      │                  DM without mention · guild mention/reply · idle presence
      │
      ▼
ai/engine.py            orchestration (ask / respond)
      │
      ├─▶ ai/request_router.py     what does this message need?
      │        • freshness classification  (search/freshness.py)
      │        • exact-tool hits (weather, FX, clock, calculator, maps, translate)
      │        • static-knowledge exemption (never search "why is the sky blue")
      │
      ├─▶ database/knowledge.py    has Nexus already verified this?
      │
      ├─▶ search/aggregator.py     collect evidence from several tools at once
      │        ├─ tools/manager.py ─▶ 20+ tools (each reports its own health)
      │        ├─ search/cache.py       freshness-aware cache + stale-while-revalidate
      │        ├─ search/ranking.py     junk filter, authority, recency decay,
      │        │                        dedupe, cross-check, conflict detection
      │        └─ search/report.py      one SearchReport the rest of the system trusts
      │
      ├─▶ ai/conversation_manager.py   assemble the prompt by priority blocks
      │        persona → evidence → verified notes → facts → user memory
      │
      ├─▶ ai/provider_manager.py       one provider call, breaker-protected failover
      │        └─ ai/providers/*.py
      │
      ├─▶ ai/verifier.py               compare the draft with the evidence
      │        fabricated links removed · unverified figures flagged ·
      │        cutoff excuses rewritten · conflicts disclosed
      │        └─ one bounded repair pass (re-ask with evidence) — never a loop
      │
      ├─▶ utils/rich_response.py       choose plain / reference / solution / code
      │        plain chat stays plain · evidence images only · long code attached
      │
      └─▶ persistence
               database/memory.py       rolling conversation window
               ai/memory_extractor.py   durable personal facts
               database/knowledge.py    verified public knowledge (+ history)
```

`engine.respond()` returns the answer **plus** the route, the report and the
verification — that metadata is what `/sources`, `/nexus status` and the tests
read.

---

# Layer responsibilities

| Layer | owns | must never |
|---|---|---|
| `bot.py` | Discord events, DM/mention/reply ingress, cog loading, health endpoint | contain AI policy |
| `commands/` | presentation, permissions, cooldowns | call providers directly |
| `ai/` | orchestration, prompting, verification, learning | invent facts itself |
| `search/` | retrieval policy: freshness, cache, ranking, reports | know what a Discord message is |
| `tools/` | one external API each, honest failures, declared TTLs | return placeholder text as success |
| `media/` | bounded voice turns, Groq speech, Discord DAVE compatibility, media helpers | persist raw voice audio or bypass `ai/engine.py` |
| `database/` | profiles, memory, facts, verified knowledge, history | hold business rules |
| `core/` | the self-updating loop | mutate user settings or config.py |
| `utils/` | settings, prompts, time, Discord presentation, permissions | make accuracy decisions |
| `api/` | HTTP surface over the same engine | reimplement pipeline logic |

---

# Accuracy mechanisms, in order of where they bite

1. **Routing** (`ai/request_router.py`) — a question is only searched when its
   answer can actually be out of date. Wrong answers usually start with a wrong
   retrieval decision, not a bad model.
2. **Freshness budgets** (`search/freshness.py`) — `instant` 5 min, `short` 6 h,
   `medium` 3 d, `long` 30 d, `static` never. The same number drives the cache
   ceiling, the recency penalty and the verifier's expectations.
3. **Tool honesty** (`tools/base.py`) — every tool declares `required_keys`,
   `ttl`, `keywords`, `searchable`, and reports failures into a `ToolHealth`
   object that removes it from selection for 15 minutes after 3 failures. A
   broken tool stops being a source of confident nonsense.
4. **Ranking and cross-check** (`search/ranking.py`) — placeholders, empty
   bodies and near-duplicates are dropped; domain authority and age adjust the
   score; independent domains corroborate, syndicated copies do not; disagreeing
   numbers become a `conflicts` entry instead of an average.
5. **Prompt assembly** (`ai/conversation_manager.py`) — evidence is injected as
   *data with rules attached* (prompt-injection resistant), and blocks are
   dropped by lowest priority when the budget overruns, never mid-sentence.
6. **Verification** (`ai/verifier.py`) — links the model cited that no tool
   returned are deleted; figures absent from the evidence cap confidence and
   trigger one repair; "I cannot access the internet" is treated as a bug and
   rewritten; residual uncertainty is disclosed to the user in one line.
7. **Learning** (`database/knowledge.py`) — only grounded answers become durable
   rows, with history, confidence, expiry and a disputed state for
   contradictions.
8. **Presentation** (`utils/rich_response.py`) — the verified outcome is rendered
   without changing its meaning. Simple replies remain plain; explanations and
   worked solutions get a focused embed between plain prose; code is split into
   copyable parts or attached as a complete replacement file. Images must come
   from retrieved HTTPS evidence, never from model-written URLs.

---

# Media paths

Music is isolated from the text pipeline:

```text
/music command → commands/music.py → Wavelink → Lavalink v4
                                             ├─ YouTube source plugin
                                             └─ LavaSrc (Spotify metadata → playable source)
```

The bot owns command policy, queues and Discord embeds; Lavalink owns searching,
decoding and audio transport. Nexus probes each node's reported plugins/sources
at startup and reconnect, delays automatic Now Playing cards past immediate
source failures, and logs full structured track exceptions. State is per guild,
bounded, and released when the channel empties or the inactivity deadline expires.

Conversational voice deliberately reuses the normal AI engine:

```text
Discord PCM → activity gate + turn segmentation → Groq STT → engine.respond()
                                         → Groq TTS → Discord PCM
```

Only completed turns are transcribed, Nexus does not listen to its own output,
decoded silence cannot open a turn, repeated transcripts are suppressed, and
raw audio is never written to the database. Transcribed text follows the
same bounded conversation-memory policy as a typed message; the optional
Discord text mirror is a separate setting. The pinned receive extension is
guarded for Discord's inbound DAVE packet order. If compatibility cannot be
established, live voice reports unavailable instead of accepting corrupt audio.
Because Discord allows one voice client per guild, a shared per-guild audio
coordinator serializes the explicit handoff between voice-chat and music modes.
Groq TTS access failures keep the live STT session active and fall back to text.

---

# Self-update path

`core/updater.py` runs one asyncio task on the bot loop (no cron, no worker):

```
every SELF_UPDATE_INTERVAL (default 6 h)
  1. runtime facts   → version, provider, model, live clock in UTC + IST
  2. tool probes     → a real query per tool; failures recorded in tool_health
  3. re-verify       → every knowledge row past its TTL is looked up again:
                        confirmed | changed (history kept) | disputed
  4. watchlist       → the topics this community keeps asking about stay warm
  5. maintenance     → expired cache entries dropped, weak rows pruned
  6. model catalog   → ai/model_catalog.py re-reads provider /models and swaps
                       retired model ids (config.py is never rewritten)
```

One cycle at a time (`asyncio.Lock`), bounded work per cycle, nothing persisted
that it cannot re-derive. See [ACCURACY.md](ACCURACY.md) for the knobs.

---

# Storage

Single SQLite file (`data/nexus.db`), WAL mode, `SCHEMA_VERSION` + diff-based
migration on startup so a deployed bot gains columns without an operator
running a script.

```
profiles            user identity, preferences, role, stats
messages            rolling conversation window (per user)
facts               durable personal facts (category-keyed, superseded, not deleted)
knowledge           verified public claims + confidence, hits, expiry, status
knowledge_history   every change to a claim, with why and provenance
tool_health         last successful probe / error per evidence tool
settings            runtime settings that must survive a restart
```

Privacy is user-facing by design: `/facts`, `/forget` and `DELETE /memory/{id}`
exist so a person can audit and erase what the bot says about them.

---

# Failure model

| Failure | What Nexus does |
|---|---|
| No API keys at all | answers from the model, says "not verified" on time-sensitive questions |
| One provider down / rate-limited | breaker rotates to the next capable provider; `self.provider` is never mutated |
| One evidence API down | excluded from selection for a cooldown window, disclosed as `N tool(s) failed` |
| Every tool empty on an `instant` question | refuse-or-hedge per `REFUSE_WHEN_UNVERIFIED`, never a fake answer |
| Search deadline exceeded | partial evidence is used, `report.stale`/`truncated` flags travel with it |
| Updater exception | logged, cycle ends, chat unaffected |
| Model returns a fabricated citation | stripped by the verifier and logged |
| Discord reports `NaN` latency during startup | `/health` returns `null`; the service remains healthy |
| Model emits a tool-call envelope | the OpenRouter provider executes/normalises it; raw tool markup is not posted |
| Mistral uses its namespace client layout | load `mistralai.client.Mistral`, with the legacy root export as fallback |
| Lavalink node is offline | text/AI remains live; music commands show the node error and setup hint |
| Last human leaves music | disconnect, clear the guild queue and cancel inactivity work |
| Voice dependency is unavailable | disable only live voice and expose the exact reason in `/voice status` and `/health` |
| Voice receive loop fails | one controlled listener restart; session-local cleanup if it cannot recover |

---

# Why it is shaped this way

The retrieval and verification stages exist so that the language model can stay
*small and free*. Nexus runs on `google/gemma-3-27b-it:free` or a local Ollama
model and still refuses to guess: the guarantee comes from the pipeline, not
from a bigger model. That is also why every stage is independently testable —
see `tests/`, which run offline with the network disabled by a conftest guard.
