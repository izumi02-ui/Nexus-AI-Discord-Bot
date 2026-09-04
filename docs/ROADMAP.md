# 🗺 Project Nexus — Roadmap

Nexus 2.0.0-alpha.2 is the **accuracy release**: retrieval policy, cross-checked
evidence, post-generation verification, and a store of knowledge that re-checks
itself.

What follows is ordered by how much accuracy each item buys per unit of work,
not by how interesting it is.

---

## Now (finish this release)

- [ ] Point the `news` tool at real publisher RSS feeds end to end and drop the
      HTML-page "feed" (it parses today, but the source is fragile).
- [x] Verify the live Discord path with OpenRouter on Render, including provider
      startup, mention replies, DMs and rich code output.
- [x] Make Render health checks startup-safe when Discord latency is not yet a
      finite number.
- [x] Add conditional rich presentation without converting ordinary chat into
      embeds: structured explanations, worked solutions, retrieved reference
      images, and complete-file delivery for oversized generated code.
- [x] Keep normal code-generation requests out of unnecessary live search while
      preserving search for current APIs, releases and documentation.
- [ ] Register the model catalog refresh on startup (currently run by the
      updater cycle and `/nexus models` only).

## Next

Detailed version of this list, with dependencies and guardrails per item, lives in
the README's [Planned features](../README.md#planned-features) section.

- [ ] **Image understanding.** The router detects attachments and the engine
      passes them through with an explicit "you cannot see this" guard, but no
      provider currently receives the image. Wire `ai/providers/*` vision calls
      where the provider supports it, and route screenshots through the OCR tool
      where it does not.
- [ ] **Follow-up questions.** When evidence is thin, Nexus should ask one
      clarifying question instead of answering partially. Cheap, and it removes
      a whole class of "confidently vague" replies.
- [ ] **Per-tool budgets.** `SEARCH_TIMEOUT` is one global deadline. Weather
      should get 4 s and finish; Wikipedia should get 8 s. Rank-based early
      exit when two domains already agree.
- [ ] **Retrieval quality eval.** Extend `tests/` with a labelled question set
      (question → expected source domain) so ranking changes are measured
      rather than eyeballed. This is the only way accuracy work stays honest.
- [ ] **`/nexus history`** — surface `knowledge_history` so a user can watch the
      bot correct itself. It already records every change; nobody can read it yet.
- [ ] **OCR fallback** — `tools/ocr.py` is a placeholder by design; make it real
      with `pytesseract` (already in requirements) while keeping it optional and
      reporting "unavailable" when the Tesseract binary is missing.
- [ ] **PDF reading and preview** — `tools/pdf_reader.py`, per-page extraction so
      citations carry page numbers, plus optional rendered previews. First new
      dependency of this project (`pypdf`); text treated as quoted-untrusted.
- [ ] **File understanding beyond plain text** — widen `tools/file_reader.py`
      (CSV/tables, code structure, chunked map-reduce for long documents) while
      keeping the root confinement and per-user isolation.
- [ ] **Image generation** — `capabilities.image_generation` already exists for
      this; add `tools/image_gen.py` + `/generate`, provenance visible, no
      real-person likenesses, separate rate limit.
- [ ] **GIF and short animation** — `tools/media_render.py`: frames → GIF with
      Pillow (already a dependency); video → GIF only where `ffmpeg` exists, and
      only from user-supplied or licensed media.

## Later

- [ ] Voice channels, image generation, dashboard, plugin system, event system,
      analytics (carried over from the original design doc, still unbuilt).
- [ ] Google Drive / Supabase sync — the local SQLite store is deliberate and
      works on Render's free tier; a hosted mirror is only worth it for
      multi-instance deployments.
- [ ] Scheduled user-visible digests ("the thing you asked about changed").
      All the parts exist: watchlist, history, diffing.
- [ ] Optional guarded git self-update for the creator (`/nexus selfupdate`) —
      decided against for now: an agent that can rewrite its own code needs a
      review gate, and there isn't one yet.

## Explicitly not planned

- Self-modifying code execution without a human review step.
- Scraping services whose terms forbid it (Google News RSS, DuckDuckGo HTML
  SERPs) — they are the easy path to a bot that stops working and starts
  guessing.
- Silent config rewrites. The updater may change *runtime* settings and repair
  model ids in memory; `config.py` stays authoritative for what a restart does.
