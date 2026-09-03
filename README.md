# 🌌 Project Nexus

An AI companion for Discord that would rather say *"I could not verify that"*
than guess.

It runs on free or local models - and is built so that the pipeline, not the
model, is what makes it trustworthy.

---

## What it does

```
you: who is the prime minister of india?
nexus: Shekhar Kumar was sworn in as prime minister on 9 June 2026, following
       the NDA's victory in the 2026 general election.
       -# Sources
       -# BBC: <https://...> · The Hindu: <https://...>
       -# ⚙️ verified · 2 domains · freshness: today · 1.9s
```

| | |
|---|---|
| **It checks, when checking is needed** | every question is classified by how fast its answer rots: weather and prices must come from a source minutes old, "why is the sky blue" is answered directly with no search at all |
| **It cross-checks** | several sources in parallel; two domains agreeing corroborates, a syndicated copy does not, and two different numbers become a visible disagreement instead of an average |
| **It verifies its own draft** | a citation no tool returned is deleted, a figure absent from the evidence triggers one repair pass, "I can't access the internet" is treated as a bug because Nexus has tools |
| **It discloses** | single source, cached, disputed, unverified - you are told what is solid and what is not, in one line under the answer |
| **It remembers, and re-checks** | verified answers become durable knowledge with confidence and expiry; a background cycle re-looks-up what went stale, updates it with history, or marks it disputed when sources contradict |
| **It repairs its own config** | a retired model id on a free tier is detected against the provider's live `/models` list and swapped, in memory, without touching your files |
| **It fails loudly** | a dead API removes that tool from selection for a while and is reported; nothing ever reaches the model as confident placeholder text |

Memory is per-user and auditable: `/facts` shows exactly what it remembers,
`/forget` deletes any of it.

---

## Quick start

```bash
git clone https://github.com/izumi02-ui/Nexus-AI-Discord-Bot
cd Nexus-AI-Discord-Bot

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env       # add a DISCORD_TOKEN, then a provider key
python bot.py
```

**Zero keys still works.** With nothing but `DISCORD_TOKEN`, Nexus answers from
Ollama or LM Studio if either is running, uses the keyless evidence sources
(Wikipedia, Open-Meteo, DuckDuckGo Instant Answers, publisher RSS, Stack
Exchange, arXiv), and tells you when an answer is not verified. Add keys to
sharpen it: `OPENROUTER_API_KEY` (many free models), `BRAVE_API_KEY` or
`GEMINI_API_KEY` (better web search), `WEATHER_API_KEY`, `GITHUB_TOKEN`.

<details>
<summary>Discord setup</summary>

1. [Developer Portal](https://discord.com/developers/applications) → New
   Application → Bot.
2. Enable **Message Content** and **Server Members** intents (privileged).
3. Copy the token into `.env` as `DISCORD_TOKEN`.
4. Invite with `bot` + `applications.commands` scopes, `Send Messages`,
   `Read Message History`, `Embed Links`.

</details>

---

## Commands

| Command | What it does |
|---|---|
| `/ask <question>` | the full pipeline: route → retrieve → answer → verify, with a grounding badge |
| `/search <query> [tool]` | the raw evidence, before any model touches it |
| `/sources` | what Nexus' last answer to you was built on |
| `/verify <claim>` | checks one statement against live sources: supported / disputed / only one place |
| `/remember`, `/forget`, `/facts` | control over what it keeps about you |
| `/tools`, `/version`, `/ping` | which sources are configured, which build is running, how fast |
| `/nexus status` | provider, grounded rate, cache, knowledge store, updater state |
| `/nexus reverify [topic]` | re-check stored knowledge right now |
| `/nexus accuracy [preset]` | `strict` / `balanced` / `fast` / `offline`, or fine-grained flags |
| `/nexus tools` · `/nexus models` | per-tool health and cooldowns · re-read provider model lists |
| `/nexus provider` · `/nexus knowledge` · `/nexus start-updating` | rotate providers, inspect the store, run a cycle |

Prefix equivalents `!ai`, `!memory`, `!status` exist for text channels without
slash access. Mentioning the bot works like `/ask`.

---

## Configuration

Behaviour is decided in `config.py`, overridable by environment variables - no
hidden defaults, and nothing is rewritten at runtime.

```bash
# accuracy
SEARCH_MODE=auto              # auto | always | never
MIN_SOURCES_FOR_GROUNDING=1   # independent domains needed to call it verified
VERIFICATION_ENABLED=true
AUTO_RETRY_WITH_SEARCH=true   # one repair pass when an answer cannot stand
REFUSE_WHEN_UNVERIFIED=false  # prefer a refusal over guessing "right now" facts
CITATION_MODE=auto            # auto | footer | inline | off

# self-update
SELF_UPDATE_ENABLED=true
SELF_UPDATE_INTERVAL=21600    # re-verify stale knowledge every 6 hours
KNOWLEDGE_TTL=86400
TOOL_PROBE_INTERVAL=1800      # health-check the evidence tools every 30 min
MODEL_AUTO_REFRESH=true       # repair retired model ids against live /models
```

Full list with comments in [`.env.example`](.env.example); the reasoning behind
each knob is in [`docs/ACCURACY.md`](docs/ACCURACY.md).

---

## Layout

```
ai/        engine, router, providers, conversation manager, verifier, memory
search/    freshness policy, cache, ranking + cross-check, evidence report
tools/     one module per external source; each declares TTLs and health
core/      the background updater (re-verification, probes, maintenance)
database/  SQLite: profiles, memory, facts, verified knowledge + history
commands/  Discord cogs: chat, memory, admin, utility
prompts/   persona, personality, accuracy policy (loaded per request)
api/       FastAPI surface over the same engine
utils/     settings, prompts, formatting, time, permissions, cooldowns
tests/     offline suite: routing, freshness, ranking, verifier, prompts
docs/      ARCHITECTURE · ACCURACY · ROADMAP · SYSTEM_DESIGN · VISION
```

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite runs with **no network and no model**: `tests/conftest.py` blocks
outbound HTTP and the pipeline is exercised against fixture evidence, so a
failing test means a policy regression rather than a flaky API.

---

## Deploying

`Procfile` runs `python bot.py`, and `web` starts a health server on `$PORT` -
built for Render's free tier, including sleeping instances: the knowledge store
and its expiry live in `data/nexus.db`, so a restart resumes with verified
facts instead of starting from nothing. Mount a disk or sync the file if you
want memory to survive a rebuild.

---

## Notes on honesty

This README describes what the code does today, not what it will do. Two limits
worth stating: retrieval quality is bounded by the sources a keyless bot may
use (add `BRAVE_API_KEY` for materially better coverage of breaking events),
and if every source in a result set repeats the same wrong number, Nexus
reports it as corroborated - which is exactly why disagreements are surfaced
rather than averaged.

---

Creator: **Izumi** (Rohit / IZ) · Special user: **Ash** (Ashey)

*Build once. Extend forever. Never assert what you cannot check.*
