# 🎯 Accuracy

How Nexus decides what it may say, and how to tune that.

---

## The short version

An answer is **grounded** when at least `MIN_SOURCES_FOR_GROUNDING` independent
domains returned text that is about the thing you asked, of decent quality, and
not in disagreement with itself. Anything else is stated with a caveat, retried
once, or refused — never presented as fact.

---

## Freshness policy

Every question is classified before it is answered, and the class decides how
old evidence may be, how long it is cached, and whether the model is even
allowed to answer from memory.

| class | examples | max age of evidence | may answer from memory? |
|---|---|---|---|
| `instant` | weather, prices, "right now", exchange rates, clock | 5 minutes | never |
| `short` | today's news, who holds a current office, latest release | 6 hours | never |
| `medium` | population, benchmarks, "best X in 2026" | 3 days | with a caveat |
| `long` | census figures, geography, official statistics | 30 days | yes |
| `static` | math, code, definitions, explanations, opinion | n/a | yes, no search at all |

Unrecognised phrasing defaults to `static`, because a bot that searches for
everything is slow, hits rate limits, and makes the model second-guess facts it
already knows correctly.

## Retrieval

- `MAX_SOURCES` results are collected from the tools the router selected,
  concurrently, under one `SEARCH_TIMEOUT` deadline.
- Results are filtered (placeholders, empty pages, tool failures), scored by
  domain authority × relevance × recency, and deduplicated across syndicated
  copies.
- Sources are cross-checked: ≥2 independent domains agreeing *corroborates*;
  two different numbers for the same quantity becomes a visible **conflict**
  instead of a quiet average.
- Cache lives `min(tool TTL, freshness budget)`; a stale-but-useful entry may
  be served once while it refreshes in the background, and the answer then says
  "answered from cached sources".

## Verification (post-generation)

`ai/verifier.py` compares the finished draft with the evidence:

1. **Links** — any URL the answer cites that no tool returned is deleted
   (markdown links degrade to their label text, so the sentence still reads).
   This is a hard filter: a fabricated citation is worse than no citation.
2. **Numbers** — money, percentages and measured quantities whose digits do not
   appear in the evidence cap confidence and force one re-ask.
3. **Refusals to look things up** — "I cannot browse the internet" / "my
   knowledge ends in ..." is a *false statement about this bot*, so the sentence
   is stripped and the question is re-asked with evidence attached.
4. **Grounding** — a time-sensitive question with no evidence and a confident
   answer gets one repair pass (forced search, then re-ask). There is no second
   retry: an unbounded loop turns a wrong answer into an expensive one.
5. **Disclosure** — whatever remains uncertain is told to the user in one short
   line: single source, sources disagree, cached, unverified figures, answered
   from Nexus' own notes.

## Knowledge

Only grounded answers are written to `knowledge`. A re-check that agrees raises
confidence; a re-check that contradicts *replaces* the value and keeps the old
one in `knowledge_history`; an unreconcilable contradiction marks the row
`disputed`, and disputed rows are down-weighted and never phrased as fact.

---

## Knobs

| setting | default | effect |
|---|---|---|
| `SEARCH_MODE` | `auto` | `always` searches every prompt, `never` disables retrieval |
| `SEARCH_TIMEOUT` | `18` | deadline for the whole evidence phase |
| `MAX_SOURCES` | `6` | how much to collect |
| `MIN_SOURCES_FOR_GROUNDING` | `1` | independent domains required to call something verified |
| `VERIFICATION_ENABLED` | `true` | off = skip checks 1–4 (keep for debugging only) |
| `AUTO_RETRY_WITH_SEARCH` | `true` | allow the single repair pass |
| `REFUSE_WHEN_UNVERIFIED` | `false` | prefer a refusal over an unverified time-sensitive answer |
| `CITATION_MODE` | `auto` | `footer` / `inline` / `off` |
| `KNOWLEDGE_TTL` | `86400` | how long a stored fact may be quoted before re-check |
| `KNOWLEDGE_MIN_CONFIDENCE` | `0.35` | below this a row is pruned |
| `OPENROUTER_WEB_SEARCH` | `false` | let the provider ground itself (paid, so opt-in) |

Admin commands (creator only): `/nexus accuracy`, `/nexus status`,
`/nexus reverify`, `/nexus tools`, `/nexus models`, `/nexus knowledge`.

---

## Known limits — stated honestly

- Retrieval quality is bounded by keyless sources. DuckDuckGo's HTML endpoints
  are CAPTCHA-gated, so the fallback engine is the Instant Answer API plus
  Wikipedia; adding `BRAVE_API_KEY` or `GEMINI_API_KEY` materially improves
  coverage of "what happened today" questions.
- Nexus verifies *against its sources*. If every source in a search result page
  repeats the same wrong number, Nexus reports that number as corroborated.
  This is why disagreements are surfaced instead of averaged.
- The verifier checks numbers and links mechanically; it cannot judge whether an
  *explanation* is subtly wrong. Complex reasoning still needs a human.
- Free-tier models will occasionally ignore the "answer only from evidence"
  instruction. The retry exists for exactly that, and its remaining failures are
  disclosed in the footer rather than hidden.
