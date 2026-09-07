The app launch, website landing page and Android download experience are
first-class parts of the Nexus brand, not afterthoughts.

Use these screenshots only as structural UX references.

Do NOT clone ChatGPT visually or pixel-for-pixel.

Keep:
- mobile drawer navigation
- settings grouping
- account hierarchy
- clean card-based settings layout

Exclude:
- Remote
- Plugins

Rebrand everything into an original Nexus/Nexy visual identity:
dark, cinematic, futuristic, premium, liquid-glass accents, smooth Framer Motion transitions.


You are now the lead full-stack/product engineer for my existing AI project
"Nexus / Nexy".

Repository:
izumi02-ui/Nexus-AI-Discord-Bot

Target branch:
Nexus-V4

MISSION
=======

Transform the existing Nexus project into the foundation of a polished
consumer AI platform with:

1. Existing Discord bot
2. Existing Nexus AI backend/API
3. New responsive web application
4. Installable PWA
5. Android-ready application architecture
6. Future Google Play Store distribution
7. User accounts and cloud-synced Nexus data
8. Subscription/membership system
9. Full owner/admin control panel

DO NOT replace the existing Nexus AI architecture.

The current repository already contains substantial systems including:
- ai/
- api/
- commands/
- database/
- media/
- search/
- tools/
- utils/
- prompts/
- tests/

The API already contains routes/modules for chat, health, memory, models,
research, search and tools.

FIRST inspect the COMPLETE Nexus-V4 repository and understand these systems
before writing frontend/backend code.

The new app must consume and extend the existing Nexus backend rather than
creating a second disconnected AI implementation.

============================================================
PHASE 0 — RESEARCH THE REQUIRED DESIGN/ANIMATION REFERENCES
============================================================

Before implementing UI, read these references.

Framer Motion:
https://www.npmjs.com/package/framer-motion?activeTab=readme

UI/UX Pro Max Skill:
https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

Liquid Glass JS:
https://github.com/dashersw/liquid-glass-js

Liquid Logo:
https://github.com/paper-design/liquid-logo

Do NOT blindly copy code from these projects.

Inspect their current APIs, licenses, browser support, performance
characteristics and integration requirements first.

Use Framer Motion as the primary React animation system where appropriate.

Use UI/UX Pro Max as a design/review reference to improve:
- hierarchy
- spacing
- typography
- responsive behavior
- navigation
- accessibility
- component consistency
- UX states
- visual polish

============================================================
PRODUCT DESIGN DIRECTION
============================================================

The screenshots supplied with this task are visual/interaction references.

DO NOT make a pixel-for-pixel ChatGPT clone.

Create an ORIGINAL Nexus identity.

The app should feel:
- premium
- futuristic
- dark
- minimal
- cinematic
- fast
- tactile
- slightly glassy
- clearly Nexus, not ChatGPT with a different logo

Use restrained liquid-glass effects rather than turning every surface into
transparent glass.

Maintain excellent readability.

Primary UX should be optimized for Android/mobile first, while expanding
beautifully to tablets and desktop.

Animations must feel physical and smooth, not gimmicky.

Respect:
prefers-reduced-motion

Avoid expensive effects on low-power/mobile devices.

============================================================
CORE NAVIGATION
============================================================

Build a responsive navigation model inspired by the supplied screenshots.

MOBILE:
Use a polished slide/drawer navigation.

DESKTOP:
Use an expandable/collapsible sidebar or equivalent desktop navigation.

Primary product destinations should include:

- Chat
- Images
- Library
- Projects
- Scheduled
- Profile / Account
- Settings

DO NOT add:
- Remote
- Plugins

Those two are explicitly excluded from this product scope for now.

The navigation must also support:
- recent chats
- search
- new chat
- rename chat
- delete/archive chat
- account/profile access

Admin must NOT appear as a normal user feature.
Expose admin navigation only to authorized admin/owner accounts.

============================================================
1. CHAT EXPERIENCE
============================================================

Chat is the main Nexus experience.

Build a premium AI chat UI connected to the EXISTING Nexus API/AI engine.

Required UX:

- new chat
- persistent conversations
- conversation history
- rename/archive/delete
- streaming responses if backend architecture supports it
- markdown
- syntax-highlighted code
- copy response/code
- retry/regenerate
- stop generation
- edit/resend user message
- loading/skeleton states
- model/status display where appropriate
- citations/source cards when Nexus returns research sources
- rich tool-result rendering
- attachments
- images where supported
- responsive composer
- auto-growing textarea
- mobile keyboard-safe layout
- scroll restoration
- sensible optimistic UI

Do not duplicate ai/engine.py or provider_manager.

Create proper API contracts/adapters between the web client and existing
Nexus services.

============================================================
2. IMAGES
============================================================

Create an Images experience prepared for Nexus image generation.

Include:
- prompt composer
- generation history
- responsive gallery
- image detail view
- download/share where supported
- delete
- reuse prompt
- loading/progress states
- error/retry states

If the current backend has no production image-generation provider, implement
the frontend/API abstraction cleanly and mark provider integration as pending.

DO NOT fake successful generations.

============================================================
3. LIBRARY
============================================================

Create a Nexus Library for user-owned AI content.

Support appropriate content such as:
- generated images
- uploaded files
- useful chat artifacts
- saved outputs

Provide:
- search
- filters
- sort
- grid/list views
- metadata
- preview
- delete/archive
- mobile-friendly file management

Do not expose arbitrary server filesystem paths.

============================================================
4. PROJECTS
============================================================

Projects are persistent workspaces.

A project may contain:
- chats
- files
- generated images
- project instructions
- project-specific context

Implement clear data ownership boundaries.

Project context should integrate with Nexus memory/context intentionally,
not by dumping every project file into every prompt.

============================================================
5. SCHEDULED
============================================================

Create Scheduled tasks UI.

Users should be able to view and manage supported Nexus scheduled jobs:
- name
- next run
- frequency
- status
- enable/disable
- edit
- delete

Design backend abstractions so a proper scheduler/worker can execute tasks
reliably.

Do not pretend a scheduler exists if the current backend does not yet provide
one.

============================================================
6. PROFILE / ACCOUNT
============================================================

Build an account/profile screen inspired structurally by the references but
with original Nexus styling.

Include:
- avatar
- display name
- email
- edit profile
- membership tier
- account management
- security
- appearance
- accent color
- notifications
- voice settings
- storage usage
- data controls
- logout

Do not expose secrets or internal IDs unnecessarily.

============================================================
7. SETTINGS
============================================================

Implement organized settings sections.

PERSONALIZATION
- Nexus behavior preferences
- response style where supported
- appearance preferences

MEMORY
- memory enabled/disabled
- user-readable memory controls
- clear explanation of what Nexus remembers
- appropriate deletion controls

APPEARANCE
- system / light / dark where supported
- accent theme
- reduced motion compatibility

VOICE
- voice selection
- STT/TTS preferences where supported
- voice feature status

NOTIFICATIONS
- relevant app notifications

STORAGE
- storage usage
- uploaded/generated content management

DATA CONTROLS
- export/delete account data flows where supported
- privacy controls

SECURITY
- sessions
- account security controls

Do not build fake toggles.
A visible setting must either work or clearly be marked unavailable.

============================================================
8. LIQUID GLASS
============================================================

Read:
https://github.com/dashersw/liquid-glass-js

The original example request was for a plain HTML page, but THIS project may
use a modern React frontend.

Do NOT force a vanilla-JS integration if it conflicts with the chosen
architecture.

Study the Container/refraction implementation and integrate it safely where
appropriate.

Good candidates:
- top navigation
- mobile navigation drawer
- floating composer controls
- selected premium cards
- modal surfaces
- membership/pricing cards

Requirements:
- real background interaction/refraction where supported
- readable foreground text
- graceful fallback when unsupported
- mobile performance testing
- no giant blur layers that destroy FPS
- accessibility preserved

============================================================
9. LIQUID METAL NEXUS LOGO
============================================================

Read:
https://github.com/paper-design/liquid-logo

It uses @paper-design/shaders-react.

Create an optional animated Nexus logo treatment.

If I provide a transparent PNG logo, support loading that asset.

Visual direction:
- dark chrome / cool metallic Nexus aesthetic
- elegant refraction
- subtle liquid movement
- premium rather than flashy

Provide:
- performant live version where practical
- static fallback
- reduced-motion fallback
- graceful fallback for weak/unsupported devices

Do not make app startup depend on a heavy shader.

Do not automatically export social media assets unless the implementation
actually supports it.

============================================================
10. MOTION SYSTEM
============================================================

Use:
https://www.npmjs.com/package/framer-motion?activeTab=readme

Build a coherent motion language:

- drawer open/close
- page transitions
- modal transitions
- card expansion
- button feedback
- chat message entrance
- skeleton/loading transitions
- tab changes
- image gallery transitions
- settings accordion transitions

Animations must generally use transform/opacity rather than layout-expensive
properties.

Target smooth Android performance.

Avoid animation overload.

============================================================
11. MEMBERSHIP / SUBSCRIPTIONS
============================================================

Build a proper membership architecture.

Possible tiers:
- Free
- Plus / Pro-style paid tier(s)

Do NOT hardcode product/pricing logic throughout the frontend.

Create server-side entitlement checks.

Membership may control:
- usage limits
- premium models
- generation limits
- storage
- selected premium features

PAYMENTS:

Use a reputable payment provider appropriate for the target deployment and
region.

Before choosing one, verify:
- India support
- web support
- Android/Play Store policy implications
- recurring subscription support
- webhook support
- fees/integration constraints

IMPORTANT:
For a future Google Play distributed Android app, review current Google Play
billing requirements before implementing digital subscriptions.

Do not design a payment flow intended to bypass app-store billing policies.

Never trust the frontend to decide whether a user is paid.

Entitlements must be confirmed server-side.

Implement:
- checkout
- success/cancel
- webhook verification
- subscription state
- renewal
- cancellation
- failed payment state
- entitlement synchronization
- billing history where supported

Never store raw card details.

============================================================
12. ADMIN PANEL — OWNER CONTROL A-Z
============================================================

Build a separate protected admin interface.

Admin authorization MUST be server-side.

Never expose admin functionality merely because the frontend hides a button.

Admin capabilities should include appropriate controls for:

DASHBOARD
- users
- active users
- subscriptions
- usage
- API/provider health
- errors
- service status

USERS
- search users
- inspect account status
- membership state
- storage/usage
- suspend/restore accounts where appropriate

MEMBERSHIP
- plans
- feature entitlements
- limits
- subscription state

AI
- available models
- provider health
- default routing configuration
- feature flags

Do NOT expose raw provider API keys to browser clients.

CONTENT/USAGE
- aggregate operational metrics
- storage usage
- task/job status

SYSTEM
- feature flags
- maintenance mode
- public notices
- application configuration that is safe to expose/edit

AUDIT
- admin action audit log

Never give admins unrestricted arbitrary shell execution from the browser.

============================================================
13. AUTHENTICATION & AUTHORIZATION
============================================================

The current API contains incomplete/minimal middleware/schema areas.

Inspect them before implementing auth.

Build proper authentication suitable for web + Android.

Requirements:
- secure password hashing if passwords are used
- secure session/token handling
- email verification if appropriate
- password reset
- logout/session invalidation
- role-based authorization
- admin role
- subscription entitlements
- ownership checks on every user resource

Never rely on client-supplied:
user_id
role
is_admin
membership

for authorization.

Do not put privileged long-lived secrets in localStorage.

============================================================
14. DATABASE / PERSISTENCE
============================================================

Inspect the current database implementation before changing it.

The existing bot uses database modules for memory, knowledge, profiles, etc.

Design a migration path suitable for a multi-user web/mobile product.

Do not casually destroy or rewrite existing Nexus memory data.

Create migrations.

Data models will likely need concepts such as:
- users
- sessions
- conversations
- messages
- projects
- project files
- library items
- scheduled jobs
- subscriptions
- entitlements
- admin audit events

Keep user data properly isolated.

============================================================
15. API HARDENING — REQUIRED BEFORE PRODUCTION
============================================================

Run ALL of these production reviews before declaring the app production-ready.

RATE LIMITING
Add rate limiting appropriate to endpoint type.

Use stricter limits on:
- login
- signup
- password reset
- verification

Use moderate limits for anonymous/public APIs and appropriate authenticated
limits for normal AI actions.

For authentication routes use both per-IP and per-account protections with
progressive/exponential backoff rather than permanent hard lockouts.

Thresholds must be configurable.

INPUT VALIDATION
Every API input must use strict schema validation:
- type
- allowed values
- min/max length
- format
- file constraints

Reject invalid input rather than relying only on escaping/sanitization.

SECRETS
Scan the complete repository for:
- API keys
- passwords
- tokens
- credentials
- accidentally committed environment archives/files

IMPORTANT:
The current repository tree contains an `env.zip` artifact.

Treat that as a security review item immediately.

Determine whether it contains secrets.
Do NOT print its contents or secrets into logs/output.

If credentials were committed, recommend:
1. remove sensitive artifact from repository
2. rotate affected credentials
3. ensure .gitignore prevents recurrence
4. consider history cleanup if necessary

All production secrets must remain server-side environment variables.

DEPENDENCY VULNERABILITIES
Audit both backend and frontend dependencies.

Report:
- package
- vulnerability
- severity
- safe remediation

Update/replace packages where compatible.

ERROR HANDLING / INFORMATION LEAKAGE
Users must never receive:
- stack traces
- filesystem paths
- SQL/database internals
- API keys
- internal provider responses containing sensitive data

Return safe public errors and retain detailed server-side structured logs.

FILE UPLOAD SAFETY
Validate:
- MIME/content signature
- allowed file types
- size
- filenames
- storage destination

Never trust extension alone.

Uploaded content must not become executable server code.

Prevent:
- path traversal
- overwrite attacks
- script execution
- unrestricted public access

============================================================
16. ANDROID + PWA
============================================================

Build mobile-first.

Required:
- safe-area support
- Android keyboard handling
- touch-friendly targets
- responsive typography
- responsive sidebar/drawer
- PWA manifest
- installable icons
- service worker strategy
- offline shell where appropriate
- reconnect handling
- sensible caching

Do NOT cache sensitive API responses indiscriminately.

Prepare the architecture for future Android packaging.

Choose an approach such as Capacitor only after checking whether it is
appropriate for this codebase.

Do not immediately introduce React Native/Flutter if that would force us to
maintain two unrelated frontends.

The goal is maximum shared UI/code between:
web
PWA
Android

============================================================
17. PERFORMANCE
============================================================

Target smooth mid-range Android devices.

Measure rather than guess.

Optimize:
- JS bundle
- lazy routes
- images
- fonts
- shader loading
- glass effects
- animation count
- long chat rendering
- virtualized large lists where useful

Liquid glass and liquid logo effects must degrade gracefully.

============================================================
18. ACCESSIBILITY
============================================================

Meet sensible WCAG AA targets.

Include:
- sufficient contrast
- semantic elements
- keyboard navigation
- focus indicators
- accessible dialogs
- screen-reader labels
- reduced motion
- large enough touch targets

Glass effects must never make text unreadable.

============================================================
19. TESTING
============================================================

Create/update tests for:

- authentication
- authorization
- resource ownership
- chat API
- memory
- projects
- library
- scheduled tasks
- membership entitlements
- payment webhook verification
- admin authorization
- rate limiting
- validation
- file uploads
- error sanitization

Frontend:
- critical components
- responsive navigation
- chat composer
- settings
- billing states
- admin route protection

Also run:
- Python tests
- frontend tests
- lint
- typecheck
- production build
- dependency audit

============================================================
20. DO NOT BREAK EXISTING NEXUS
============================================================

The Discord bot must continue functioning.

Do not break:
- Discord commands
- AI engine
- provider manager
- memory
- research/search
- tools
- voice/music architecture
- prompts
- existing tests

The web/mobile product should sit cleanly alongside the Discord bot and share
the Nexus backend where appropriate.

============================================================
IMPLEMENTATION STRATEGY
============================================================

DO NOT attempt this entire product as one giant blind code dump.

First produce an implementation plan based on the ACTUAL repository.

Then implement in clean milestones.

Suggested product milestones:

M1 — Architecture + security audit
M2 — Web frontend shell/design system
M3 — Authentication + users
M4 — Core Nexus Chat
M5 — conversations/history
M6 — Library + Projects
M7 — Images
M8 — Scheduled
M9 — settings/profile
M10 — subscriptions/payments
M11 — admin panel
M12 — PWA/Android packaging
M13 — security/performance/accessibility hardening
M14 — production readiness

Do not reorder existing Nexus backend roadmap files without explicit reason.
This milestone list is for the NEW application layer.

============================================================
FIRST RESPONSE REQUIRED FROM YOU
============================================================

Before changing code, return:

1. Current Nexus-V4 architecture you found
2. Existing components we can reuse
3. Missing components
4. Security issues discovered
5. Proposed frontend stack and WHY
6. Proposed backend additions and WHY
7. Proposed database migration strategy
8. Proposed authentication architecture
9. Proposed payment architecture
10. Proposed Android/PWA strategy
11. Exact new directory/file structure
12. Milestone-by-milestone implementation plan
13. Risks / compatibility concerns
14. Which existing files must NOT be rewritten
15. Any assumptions that require verification

After that, begin M1 only.

Do not invent features as already working.
Do not use placeholder implementations and call them production-ready.
Do not silently remove existing functionality.
Do not expose secrets.

============================================================
21. CINEMATIC APP LAUNCH / OPENING EXPERIENCE
============================================================

The Nexus app must have a distinctive opening experience.

Do NOT use a generic spinner or plain static splash screen.

Create a short premium Nexus launch sequence using the visual language of the
product:

- Nexus logo reveal
- subtle liquid-metal motion
- controlled refraction/glass distortion
- soft depth/parallax
- smooth transition into the main app
- Framer Motion for UI transitions where appropriate
- shader animation only if performance remains acceptable

Target duration:
approximately 1–2 seconds for the full launch sequence.

Requirements:
- Android-first performance
- no long blocking intro
- first meaningful UI should load quickly
- cache/preload required assets
- skip/reduce repeated intro animation on frequent launches if useful
- respect prefers-reduced-motion
- static lightweight fallback on weak/unsupported devices
- do not make shader initialization a requirement for app startup
- avoid flashing, excessive blur or unreadable transitions

The transition from splash -> app must feel continuous, not like two unrelated
screens.

Create a reusable Nexus motion system for:
- initial app launch
- authenticated launch
- signed-out launch
- route transitions
- drawer navigation
- chat opening
- modal/sheet opening

============================================================
22. OFFICIAL NEXUS DOWNLOAD WEBSITE
============================================================

The Nexus website must also function as the official application download page.

Users should be able to download the Android version of Nexus directly from
the official website.

Build a polished Download section/page containing:

- "Download Nexus for Android"
- current stable version
- release date
- APK size
- minimum supported Android version
- release notes / changelog
- architecture information if multiple APK variants exist
- checksum/hash for download verification where practical
- clear install instructions
- update information

Do not expose arbitrary filesystem download paths.

Use a controlled release source such as:
- GitHub Releases
- secure object storage
- CDN
or another appropriate production release system.

The website should retrieve current release metadata through a safe backend
endpoint or trusted release feed rather than hardcoding every version into the
frontend.

Design the release architecture so future releases can automatically update the
Download page.

============================================================
23. ANDROID RELEASE ARCHITECTURE
============================================================

Prepare Nexus for two distribution channels:

A. Direct Android APK distribution from the official Nexus website
B. Future Google Play Store distribution

These channels must share as much application code as possible.

For direct APK releases:
- produce signed release builds
- never commit signing keys or keystore passwords
- keep signing credentials in secure CI secrets
- version every build correctly
- generate release artifacts in CI
- attach artifacts to the chosen release platform
- optionally publish SHA-256 checksum files
- retain previous release metadata where appropriate

Do NOT put a debug APK on the production download page.

For future Google Play distribution:
- prepare Android App Bundle support where required
- maintain package/application ID stability
- use proper versionCode/versionName strategy
- review current Play Store billing and policy requirements before release

Do not implement mechanisms intended to bypass platform security or billing
rules.

============================================================
24. WEBSITE DOWNLOAD UX
============================================================

On desktop:
- show a prominent Android download card
- optional QR code that points to the official Nexus download page

On Android:
- show a direct "Download for Android" CTA
- detect platform only for improving UX, never for authorization

On unsupported platforms:
- still let users use Nexus Web
- clearly show Android availability
- do not fake unavailable native versions

Include states for:
- fetching latest release
- release unavailable
- download failure
- maintenance
- update available

The design must use the same original Nexus visual system:
dark cinematic UI, restrained liquid glass, smooth motion and premium branding.


============================================================
25. PRODUCTION AUTHENTICATION & REAL VERIFICATION
============================================================

Build a REAL production authentication system.

Do NOT use fake OTPs, mock login buttons, placeholder verification screens,
or client-only authentication.

Users should be able to sign up / sign in using:

1. Email + password
2. Email OTP / verification code
3. Phone number + OTP
4. GitHub OAuth
5. Optional additional OAuth providers later

The authentication architecture must work for:
- Web
- PWA
- Android app
- future Play Store release

------------------------------------------------------------
EMAIL AUTH
------------------------------------------------------------

Implement:

- signup with email/password
- email verification
- login
- logout
- forgot password
- password reset
- resend verification
- secure session invalidation
- change email
- change password

Passwords:
- hash securely server-side using a modern password hashing algorithm
- never store plaintext passwords
- never log passwords
- never send password hashes to the frontend

Email verification:
- generate cryptographically secure one-time codes/tokens
- codes must expire
- codes must be single-use
- resend must be rate limited
- verification attempts must be rate limited

Do not reveal whether an email exists where doing so would enable account
enumeration.

------------------------------------------------------------
EMAIL OTP
------------------------------------------------------------

Support OTP-based email login/verification.

Requirements:

- random cryptographically secure OTP
- short expiration
- one-time use
- attempt limits
- resend cooldown
- rate limit by:
  - account/email
  - IP
  - device/session where appropriate

Store only a secure representation of verification tokens where possible.

Never hardcode OTP values.

Use a real email delivery provider in production.

Keep provider credentials server-side.

Examples may include providers such as:
- Resend
- Postmark
- SendGrid
- AWS SES

Choose after checking current pricing/support for the deployment environment.

------------------------------------------------------------
PHONE NUMBER OTP
------------------------------------------------------------

Implement real phone verification architecture.

Use a reputable provider such as:
- Firebase Authentication
- Twilio Verify
- another production OTP verification provider

Before choosing, verify:
- India support
- SMS pricing
- Android/web support
- abuse protections

Requirements:

- international E.164 phone format
- OTP expiration
- resend cooldown
- attempt limits
- anti-spam/anti-abuse checks
- rate limiting
- do not expose OTP provider secrets to frontend

Do NOT build your own raw SMS gateway.

------------------------------------------------------------
GITHUB LOGIN
------------------------------------------------------------

Add GitHub OAuth authentication.

Requirements:

- OAuth Authorization Code flow
- secure state/CSRF protection
- secure callback validation
- server-side token handling where appropriate
- account linking support
- GitHub account should be linkable to an existing Nexus account

Do not create duplicate Nexus accounts just because the same user uses a
different login provider.

Design account linking around a canonical Nexus user identity.

------------------------------------------------------------
ACCOUNT LINKING
------------------------------------------------------------

A single Nexus account may have multiple auth identities:

- password/email
- email OTP
- phone
- GitHub
- future OAuth providers

Create a safe identity-linking model.

Never merge accounts based only on unverified matching profile data.

Require a verified identity before linking.

============================================================
26. SESSION SECURITY
============================================================

Build production session security.

Requirements:

- secure HTTP-only cookies for web sessions where appropriate
- Secure flag
- SameSite protection
- CSRF protection where required
- access/refresh token rotation if token-based auth is used
- session revocation
- logout-all-devices
- session/device list
- automatic expiry
- suspicious login handling

Do NOT store privileged long-lived access tokens in localStorage.

Android session storage must use platform-secure storage.

Do not trust:
- user_id
- role
- admin
- membership
- email_verified

from frontend request bodies.

All authorization must be determined server-side.

============================================================
27. DATABASE ARCHITECTURE
============================================================

DO NOT use Google Drive as the primary application database.

Google Drive is not suitable as the transactional database for:
- users
- sessions
- OTP state
- conversations
- messages
- permissions
- subscriptions
- admin state
- scheduled tasks
- entitlements

Use a real transactional database.

Preferred architecture:
PostgreSQL.

Possible managed providers:
- Supabase Postgres
- Neon
- Railway Postgres
- another managed PostgreSQL provider

Choose based on:
- deployment compatibility
- pricing
- backups
- connection limits
- migrations
- Android/web backend use

Use migrations.

Core tables should include concepts such as:

users
auth_identities
email_verifications
phone_verifications
sessions
devices
conversations
messages
projects
project_members
project_files
library_items
scheduled_jobs
subscriptions
entitlements
admin_roles
admin_audit_log

Every user-owned resource must include proper ownership/authorization checks.

============================================================
28. GOOGLE DRIVE ROLE
============================================================

Google Drive MAY be used as an OPTIONAL storage/backup integration.

Valid uses:
- user export backups
- admin backups
- generated archive export
- large user-owned file copies
- optional project export/import

Do NOT use Google Drive as the source of truth for auth or transactional data.

If Google Drive integration is added:

- use official Google OAuth
- request minimum scopes
- never expose refresh tokens
- encrypt sensitive stored credentials server-side
- isolate user Drive access per user
- handle revoked permissions cleanly
- never assume Drive is always available

For database backup:
- generate encrypted backup artifacts server-side
- upload backups to controlled storage/Drive
- keep backup metadata in the real database
- support restore verification

============================================================
29. ACCOUNT SECURITY UI
============================================================

Add a real Security section in Nexus Settings.

Show:

- verified email status
- verified phone status
- linked GitHub account
- password status
- active sessions
- devices
- login history
- logout current session
- logout all devices
- linked providers
- recovery options

Users must be able to:

- verify email
- verify phone
- link/unlink GitHub
- change password
- revoke sessions

Sensitive actions should require recent authentication/re-authentication.

============================================================
30. ADMIN AUTH CONTROL
============================================================

Admin panel should include safe account-management tools:

- search user
- verified email/phone status
- auth providers
- account status
- session count
- membership
- suspension state

Admin must NOT see:
- passwords
- OTP codes
- password hashes
- raw OAuth tokens
- refresh tokens

Every admin action must be logged in the admin audit log.

============================================================
31. AUTH TESTS REQUIRED
============================================================

Before production, test:

- email signup
- email verification
- expired OTP
- reused OTP
- brute-force OTP attempts
- resend cooldown
- password reset
- phone OTP
- GitHub OAuth
- OAuth state validation
- account linking
- duplicate account prevention
- logout
- logout all devices
- session expiration
- revoked session
- unauthorized resource access
- admin privilege checks
- rate limiting
- account enumeration resistance

Do not claim authentication is production-ready until these flows pass.





