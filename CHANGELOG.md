# Nexus Changelog

---

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
