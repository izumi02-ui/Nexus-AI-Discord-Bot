# NEXUS MODEL IDENTITY — CODEX SPEC

Repository: `izumi02-ui/Nexus-AI-Discord-Bot`
Branch: `Nexus-V4`

Read the CURRENT implementation before changing anything.

## Identity

- **Nexy** = public AI/assistant name
- **Nexus** = product/platform name
- **Alpha - V1 / Alpha - V2 / Alpha - V3 / Alpha - V4** = public model generations
- Actual third-party providers/models = private backend implementation details

## Public models

Normal users must ONLY see:

- Alpha - V1
- Alpha - V2
- Alpha - V3
- Alpha - V4

This rule applies everywhere:
Discord, Website, Web App, PWA, Android App, future Play Store app, Settings,
chat header, model selector, account preferences, API responses, conversation
metadata, usage/subscription pages, and user-facing admin previews.

Never expose normal users to raw provider/model names or IDs such as OpenRouter,
Groq, Gemini, OpenAI, Mistral, google/..., openai/..., meta-llama/... etc.

## One canonical model registry

Create ONE server-side public-model registry used by:

- Discord `/nexus models`
- Website model selector
- PWA model selector
- Android model selector
- public `/models` API
- admin model management

Do not hardcode separate Alpha lists in every client.

A future `Alpha - V5` should be addable centrally.

## Internal mapping

Public generations map server-side to private backend configurations:

```text
Alpha - V1 -> private backend configuration
Alpha - V2 -> private backend configuration
Alpha - V3 -> private backend configuration
Alpha - V4 -> private backend configuration
```

Use the EXISTING Nexus provider manager. Do not create a second AI architecture.

Environment/config support:

```env
NEXUS_MODEL_ALPHA_V1=
NEXUS_MODEL_ALPHA_V2=
NEXUS_MODEL_ALPHA_V3=
NEXUS_MODEL_ALPHA_V4=
NEXUS_DEFAULT_PUBLIC_MODEL=alpha-v4
```

Raw mappings must never be returned to normal clients.

## Real model switching

Model selection must actually change the mapped backend profile.

Persist only public IDs:

```text
alpha-v1
alpha-v2
alpha-v3
alpha-v4
```

Example:

```json
{"selected_model":"alpha-v4"}
```

Never require Web/Android clients to store raw third-party model IDs.

For authenticated users, persist model preference to their Nexus account where
appropriate so selection can remain consistent across devices.

## Web / Android selector

Website and Android must show the SAME public names:

```text
Alpha - V1
Alpha - V2
Alpha - V3
Alpha - V4
```

Mobile: use a touch-friendly animated bottom sheet.
Desktop: use a dropdown/popover.
Use Framer Motion where appropriate.

Include:
- selected state
- switching/loading state
- unavailable state
- error/rollback state
- persistent selection
- no fake successful switch

Safe labels may include `Recommended`, `Latest`, `Temporarily unavailable`, or
membership requirements. Never leak the private provider behind an outage.

## Public API

Normal model API should return safe data conceptually like:

```json
{
  "models":[
    {"id":"alpha-v1","name":"Alpha - V1"},
    {"id":"alpha-v2","name":"Alpha - V2"},
    {"id":"alpha-v3","name":"Alpha - V3"},
    {"id":"alpha-v4","name":"Alpha - V4"}
  ],
  "default":"alpha-v4"
}
```

Do not expose normal users to `provider`, `provider_model`, raw model IDs,
credentials, tokens, or private endpoints.

## Discord privileged operators

Use environment configuration:

```env
NEXUS_PRIVILEGED_USER_IDS=1169870987135823876,1118913738515427359
```

Do NOT scatter these IDs through source files.

These IDs grant Discord-side Nexus operator access only. They are NOT future
Web admin authentication.

Privileged operators must retain appropriate access to existing functionality
around:

```text
/nexus models
/nexus provider
/nexus providers
/nexus tools
/nexus status
/nexus start-updating
/nexus version
```

and Nexus/Music/Voice diagnostics.

Preserve existing command names if the repository differs slightly. Do not
create duplicate commands unnecessarily.

Privileged diagnostics may show actual provider/model IDs, provider health,
breaker/cooldown/fallback state, but NEVER secrets.

## Nexy identity

Normal public branding:

```text
Nexy
Nexus Alpha - V4
```

If a normal user asks what model/LLM powers Nexy, identify the PUBLIC generation.

Example:

```text
I'm Nexy, currently running Nexus Alpha - V4.
```

Do not reveal the raw backend model ID to normal users. Do not lie about
capabilities. It is acceptable to explain that Nexus can route through different
underlying AI infrastructure while keeping implementation details private.

## Creator / origin response

For natural questions like:

- Who created you?
- Who made you?
- Who created Nexus?
- Who made Nexy?
- Who is your creator?
- Tumhe kisne banaya?
- Nexus/Nexy ko kisne banaya?

Use the configured Nexus response:

```text
Created by Nexus.
Official Nexus Discord: <configured server URL>
```

Configure:

```env
NEXUS_DISCORD_SERVER_URL=https://discord.gg/vWstDvyUPW
```

Do not scatter the URL throughout code.

Integrate identity into the existing prompt architecture, preferably the
existing creator prompt plus safe runtime context. Never expose unrelated
environment variables to the model.

## Status and version

Normal status should use public branding:

```text
Nexy
Status: Online
Model: Alpha - V4
Verification: Ready
Memory: Ready
```

Version may show:

```text
Nexy
Nexus Alpha - V4
App version: <current Nexus application version>
```

Public generation and application semantic version are separate.

## Membership

Public generations may later have plan requirements, e.g. some Alpha versions
being membership-only. Do not hardcode restrictions until the membership system
defines them.

All entitlements must be verified server-side. Never trust client flags like
`premium=true` or `model_unlocked=true`.

## Security

Public model masking is product abstraction, not security.

Never send secrets/internal credentials to a client and merely hide them in UI.

Never expose:
- API keys
- OAuth secrets
- passwords
- auth tokens
- database credentials
- Lavalink password
- signing credentials

Authorization must happen server-side.

## Tests required

Verify:

1. Discord normal users see only Alpha public models.
2. Website normal users see only Alpha public models.
3. Android/PWA normal users see only Alpha public models.
4. Public `/models` response contains no raw provider/model IDs.
5. Alpha selection actually changes the mapped backend profile.
6. Selected public model persists correctly.
7. Invalid model IDs are rejected.
8. Unavailable generations fail gracefully.
9. Privileged Discord users can access internal diagnostics.
10. Ordinary users cannot access privileged diagnostics.
11. No diagnostic path exposes secrets.
12. Creator questions use `NEXUS_DISCORD_SERVER_URL`.
13. Model questions return the current public Alpha generation.
14. Discord/Web/Android share the same registry.
15. Future Alpha generations do not require duplicated client definitions.
16. Existing provider fallback remains functional.
17. Verification, memory, tools, music and voice remain unaffected.

## Final rule

**Nexy is the AI. Nexus is the platform. Alpha - V1/V2/V3/V4 are the public
models. The actual provider/LLM is private backend infrastructure.**

Keep this identity consistent across Discord, Website, Web App, PWA, Android,
APIs, Settings, model selectors, status screens and future Nexus clients.
