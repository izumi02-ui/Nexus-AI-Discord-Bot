# Nexy Music and Live Voice

**Version:** Nexus 1.4.0-alpha.V4
**Status:** shipped on the `Nexus-V4` branch

Nexus has two voice-channel modes. Music uses a Lavalink v4 node so decoding
and streaming do not block the bot process. Live conversation receives a
spoken turn, transcribes it with Groq Whisper, sends the text through the same
verified Nexus engine used by chat, and speaks the answer with Groq's female
`hannah` voice.

One Discord bot account can use only one voice protocol connection in a guild.
A shared per-guild coordinator serializes that ownership: starting music ends
live conversation there, and starting live conversation ends music there.
Other guilds remain independent, and disconnect cleanup releases ownership.

## Music commands

`/music help` lists the complete command surface in Discord.

| Area | Commands |
|---|---|
| Start | `join`, `play`, `playnext` |
| Playback | `pause`, `resume`, `skip`, `previous`, `replay`, `stop` |
| Queue | `queue`, `remove`, `move`, `jump`, `shuffle`, `clear` |
| Sound | `volume`, `seek`, `loop`, `autoplay`, `filter` |
| Session | `nowplaying`, `status`, `disconnect`, `leave`, `help` |

Searches, direct HTTP audio, YouTube links and playlists are supported by the
YouTube plugin. Spotify links and playlists are resolved by LavaSrc and mirrored
to a playable source; Spotify's Web API itself does not provide audio streams.
Nexus intentionally has no download command and does not reproduce lyrics.

The player includes artwork embeds, requester data, interactive controls,
per-guild queues and locks, a configurable queue cap, autoplay, looping,
filters, idle disconnect, last-human disconnect, and clean node failure output.
Admins and members with the configured `MUSIC_DJ_ROLE` may recover a player
from another voice channel.

At startup and after every node reconnect, Nexus reads Lavalink's authenticated
info endpoint and records whether LavaSrc, its Spotify source, the modern
YouTube plugin, and the YouTube source actually loaded. `/music status` exposes
those results instead of assuming that the deployed YAML loaded correctly.

`Now Playing` is scheduled only after Lavalink sends `TrackStart` and the track
survives a short configurable grace period. An immediate `TrackException`
cancels the card and logs the node, source, track identifier, exception
message, severity, and cause. Duplicate exception events produce one user
notice. A failed Spotify mirror may perform one metadata-based YouTube fallback;
the retry guard prevents loops and the remaining queue keeps its order. A failed
track is also bypassed safely when queue looping is enabled, so it cannot replay
forever.

## Live conversation commands

| Command | Behaviour |
|---|---|
| `/voice start consent:true` | join and begin listening |
| `/voice join consent:true` | alias for start |
| `/voice mute` / `unmute` | pause or resume transcription |
| `/voice say <text>` | speak a typed line with the configured voice |
| `/voice status` | show Groq, FFmpeg and Discord DAVE readiness |
| `/voice stop` / `leave` | delete the session buffers and disconnect |

This is near-real-time, turn-based conversation, not simultaneous full duplex:
a short silence closes each spoken turn. Decoded audio is bounded in memory and
limited to eight simultaneous speaker buffers, then released after
transcription; Nexus does not save recordings. The start command
requires confirmation that everyone present knows spoken turns are transcribed.
Orpheus currently accepts 200 input characters, so the spoken answer is kept
under that limit while the optional text mirror retains the detailed response.
The transcribed text follows Nexus' normal bounded conversation-memory policy,
which users can inspect or erase through `/facts` and `/forget`. Posting a
readable copy in the command channel is controlled independently with
`VOICE_TRANSCRIPTS`.

Decoded silence and low-level keepalive packets are rejected by an RMS gate
before an utterance can open. Trailing silence does not count toward the
minimum speaking duration, and identical transcriptions from one user are
suppressed for a short configurable window. If Groq denies Orpheus access or
reports that its terms still need acceptance, Nexus keeps STT/listening active
and leaves the generated answer available as text. It sends one safe explanation
per model/error state instead of repeating raw API JSON every turn, and later
turns silently retry TTS so access can recover without reopening the session.

Discord requires DAVE/E2EE for voice. The pinned receive extension has not yet
shipped inbound DAVE handling, so `media/dave_compat.py` applies a guarded,
idempotent compatibility layer and exposes its state in `/voice status` and
`GET /health`. Remove that layer only after the upstream package ships an
equivalent implementation and the regression test passes without it.

## Deploy the Lavalink node on Render

Keep the Python bot service exactly as it is. Create a **second** Render Web
Service from the same repository:

1. Choose Docker as the runtime.
2. Set the root directory to `deploy/lavalink`.
3. Add `LAVALINK_PASSWORD`, `SPOTIFY_CLIENT_ID`, and
   `SPOTIFY_CLIENT_SECRET` to that service. `SPOTIFY_COUNTRY_CODE=US` is
   optional.
4. Deploy it and copy its `https://...onrender.com` URL.
5. In the Python bot service, set `LAVALINK_URI` to that URL and
   `LAVALINK_PASSWORD` to the identical password, then redeploy.

The included image pins Lavalink `4.2.2`, YouTube plugin `1.18.2`, and LavaSrc
`4.8.3`. When any pin changes, verify all three together before production.
Do not use an unknown public Lavalink node for a production community bot.

## Required Lavalink configuration

The repository contains the complete file at `deploy/lavalink/application.yml`.
These required sections belong on the **Lavalink service**, not in the Python
bot service:

```yaml
lavalink:
  plugins:
    - dependency: "dev.lavalink.youtube:youtube-plugin:1.18.2"
      snapshot: false
    - dependency: "com.github.topi314.lavasrc:lavasrc-plugin:4.8.3"
      snapshot: false
  server:
    password: "${LAVALINK_PASSWORD}"
    sources:
      youtube: false
      http: true

plugins:
  youtube:
    enabled: true
    allowSearch: true
    allowDirectVideoIds: true
    allowDirectPlaylistIds: true
    clients:
      - MUSIC
      - ANDROID_VR
      - WEB
      - WEBEMBEDDED
  lavasrc:
    providers:
      - 'ytsearch:"%ISRC%"'
      - "ytsearch:%QUERY%"
    sources:
      spotify: true
    spotify:
      clientId: "${SPOTIFY_CLIENT_ID}"
      clientSecret: "${SPOTIFY_CLIENT_SECRET}"
      countryCode: "${SPOTIFY_COUNTRY_CODE:US}"
```

After changing a plugin version, either Spotify credential, `sources`, or the
YouTube client list, restart/redeploy the Lavalink service. Restarting only the
Python bot cannot reload a Lavalink plugin. After restart, `/music status` must
show **LavaSrc: loaded**, **Spotify resolution: ready**, **modern YouTube
plugin: loaded**, and **YouTube source: ready**.

## Required environment

```env
MUSIC_ENABLED=true
LAVALINK_URI=https://YOUR-LAVALINK-SERVICE.onrender.com
LAVALINK_PASSWORD=USE_THE_SAME_STRONG_PASSWORD_ON_BOTH_SERVICES
SPOTIFY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET
SPOTIFY_COUNTRY_CODE=US
MUSIC_START_GRACE_SECONDS=1.5
MUSIC_SPOTIFY_FALLBACK=true
MUSIC_NODE_PROBE_TIMEOUT=8

VOICE_CHAT_ENABLED=true
GROQ_API_KEY=YOUR_GROQ_API_KEY
VOICE_STT_MODEL=whisper-large-v3-turbo
VOICE_TTS_PROVIDER=groq
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=hannah
VOICE_TTS_TEXT_FALLBACK=true
VOICE_RMS_THRESHOLD=250
VOICE_DUPLICATE_WINDOW_SECONDS=12
VOICE_ERROR_COOLDOWN_SECONDS=30
```

The Spotify credentials must exist on the Lavalink service for Spotify link
resolution. They may also remain on the Python service for Nexus search cards.

## Discord permissions

Invite Nexus with `bot` and `applications.commands`, then allow View Channel,
Send Messages, Embed Links, Connect, Speak, and Use Voice Activity. The bot
must also be able to read the command channel. Users need permission to use
application commands and connect to the selected voice channel.

## Diagnostics

- `/music status` shows node connection, active players, queue state, loaded
  plugins, and usable Spotify/YouTube sources.
- `/voice status` shows STT/TTS configuration, FFmpeg and DAVE readiness.
- `GET /health` exposes both media subsystems for Render monitoring.
- If Spotify fails but YouTube works, check that both Spotify keys exist on the
  **Lavalink** service and that `/music status` reports LavaSrc plus Spotify.
- If every music request fails, compare `LAVALINK_URI` and password on both
  services.
- If voice joins but cannot hear, check `/voice status` for DAVE and verify the
  bot has `Connect`, `Speak`, and `Use Voice Activity` permissions.
- If quiet speakers are missed, lower `VOICE_RMS_THRESHOLD` gradually. If room
  noise creates false turns, raise it gradually; `/voice status` shows the
  active value.
- Groq Orpheus must be enabled and its terms accepted for the exact organization
  and project that issued `GROQ_API_KEY`. An allowed-model checkbox on a
  different project does not change the API key's access. Listening no longer
  needs `/voice unmute` after a TTS-only denial; text fallback stays active and
  later turns retry speech automatically.
- When a track resolves but produces no audio, search the bot logs for
  `Lavalink track exception`. The line includes the source, identifier, node,
  severity, message, and cause needed to identify a YouTube/plugin failure.
