# Nexy Music and Live Voice

**Version:** Nexus 3.0.0-alpha.1
**Status:** shipped on the `Nexus-V3` branch

Nexus has two voice-channel modes. Music uses a Lavalink v4 node so decoding
and streaming do not block the bot process. Live conversation receives a
spoken turn, transcribes it with Groq Whisper, sends the text through the same
verified Nexus engine used by chat, and speaks the answer with Groq's female
`hannah` voice.

One Discord bot account can use only one voice protocol connection in a guild.
Starting music ends live conversation there; starting live conversation ends
music there. Other guilds remain independent.

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
   `SPOTIFY_CLIENT_SECRET` to that service.
4. Deploy it and copy its `https://...onrender.com` URL.
5. In the Python bot service, set `LAVALINK_URI` to that URL and
   `LAVALINK_PASSWORD` to the identical password, then redeploy.

The included image pins Lavalink `4.2.2`, YouTube plugin `1.18.2`, and LavaSrc
`4.8.3`. When any pin changes, verify all three together before production.
Do not use an unknown public Lavalink node for a production community bot.

## Required environment

```env
MUSIC_ENABLED=true
LAVALINK_URI=https://YOUR-LAVALINK-SERVICE.onrender.com
LAVALINK_PASSWORD=USE_THE_SAME_STRONG_PASSWORD_ON_BOTH_SERVICES
SPOTIFY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET

VOICE_CHAT_ENABLED=true
GROQ_API_KEY=YOUR_GROQ_API_KEY
VOICE_STT_MODEL=whisper-large-v3-turbo
VOICE_TTS_MODEL=canopylabs/orpheus-v1-english
VOICE_TTS_VOICE=hannah
```

The Spotify credentials must exist on the Lavalink service for Spotify link
resolution. They may also remain on the Python service for Nexus search cards.

## Discord permissions

Invite Nexus with `bot` and `applications.commands`, then allow View Channel,
Send Messages, Embed Links, Connect, Speak, and Use Voice Activity. The bot
must also be able to read the command channel. Users need permission to use
application commands and connect to the selected voice channel.

## Diagnostics

- `/music status` shows node connection, active players and queue state.
- `/voice status` shows STT/TTS configuration, FFmpeg and DAVE readiness.
- `GET /health` exposes both media subsystems for Render monitoring.
- If Spotify fails but YouTube works, check LavaSrc and the two Spotify keys on
  the Lavalink service.
- If every music request fails, compare `LAVALINK_URI` and password on both
  services.
- If voice joins but cannot hear, check `/voice status` for DAVE and verify the
  bot has `Connect`, `Speak`, and `Use Voice Activity` permissions.
