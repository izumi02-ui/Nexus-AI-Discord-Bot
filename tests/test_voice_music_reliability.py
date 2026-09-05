"""Focused regression tests for Nexus V4 voice/music failure handling."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import wavelink

from media.audio_coordinator import GuildAudioCoordinator
from media.music_resolver import (
    LavalinkFailure,
    NodeCapabilities,
    dedupe_tracks,
    fallback_search_query,
    parse_spotify_request,
    select_fallback_track,
)
from media.speech import (
    SpeechModelAccessError,
    SpeechModelTermsRequired,
    classify_speech_access_error,
)


class FakeTrack:
    def __init__(
        self,
        identifier: str,
        *,
        title: str = "Song",
        author: str = "Artist - Topic",
        source: str = "youtube",
        uri: str | None = None,
        extras=None,
    ):
        self.identifier = identifier
        self.title = title
        self.author = author
        self.source = source
        self.uri = uri or f"https://youtube.com/watch?v={identifier}"
        self.extras = extras or {}


@pytest.mark.parametrize(
    ("url", "kind"),
    [
        ("https://open.spotify.com/track/abc123?si=value", "track"),
        ("https://open.spotify.com/album/abc123", "album"),
        ("https://open.spotify.com/playlist/abc123", "playlist"),
        ("https://open.spotify.com/intl-de/track/abc123", "track"),
        ("spotify:playlist:abc123", "playlist"),
    ],
)
def test_spotify_track_album_and_playlist_detection(url, kind):
    request = parse_spotify_request(url)
    assert request is not None
    assert request.kind == kind
    assert request.identifier == "abc123"


def test_non_spotify_and_unsupported_spotify_urls_are_not_misclassified():
    assert parse_spotify_request("https://youtube.com/watch?v=abc") is None
    assert parse_spotify_request("https://open.spotify.com/artist/abc") is None


def test_node_capability_probe_detects_lavasrc_spotify_and_youtube_plugin():
    info = {
        "sourceManagers": ["http", "spotify", "youtube"],
        "plugins": [
            {"name": "lavasrc-plugin", "version": "4.8.3"},
            {"name": "youtube-plugin", "version": "1.18.2"},
        ],
    }
    capabilities = NodeCapabilities.from_info("nexus-main", info)

    assert capabilities.probed is True
    assert capabilities.lavasrc_loaded is True
    assert capabilities.spotify_available is True
    assert capabilities.youtube_plugin_loaded is True
    assert capabilities.youtube_available is True


def test_resolver_dedupe_preserves_order_and_fallback_prefers_an_alternate():
    failed = FakeTrack("same", title="A Song")
    duplicate = FakeTrack("same", title="A Song")
    alternate = FakeTrack("different", title="A Song (Official Audio)")

    assert dedupe_tracks([failed, duplicate, alternate]) == [failed, alternate]
    assert select_fallback_track([duplicate, alternate], failed) is alternate
    assert fallback_search_query(failed) == "A Song Artist"


def test_lavalink_exception_fields_are_preserved_for_logging():
    failure = LavalinkFailure.from_exception(
        {"message": "video unavailable", "severity": "fault", "cause": "403"}
    )

    assert failure.message == "video unavailable"
    assert failure.severity == "fault"
    assert failure.cause == "403"


def test_groq_terms_and_permission_errors_are_classified_specifically():
    terms = RuntimeError(
        "400 {'error': {'code': 'model_terms_required', "
        "'message': 'requires terms acceptance'}}"
    )
    classified = classify_speech_access_error(
        terms,
        "canopylabs/orpheus-v1-english",
        operation="tts",
    )
    assert isinstance(classified, SpeechModelTermsRequired)
    assert classified.operation == "tts"

    permission = RuntimeError("permission denied for this model")
    permission.status_code = 403
    classified = classify_speech_access_error(
        permission,
        "canopylabs/orpheus-v1-english",
        operation="tts",
    )
    assert isinstance(classified, SpeechModelAccessError)
    assert classified.code == "model_access_denied"


def test_unrelated_tts_errors_remain_generic():
    assert classify_speech_access_error(
        RuntimeError("connection timed out"),
        "voice-model",
        operation="tts",
    ) is None


def test_tts_access_failure_keeps_voice_worker_listening():
    from commands.voice import VoiceSession
    from media.voice_buffer import Utterance

    async def scenario():
        session = object.__new__(VoiceSession)
        session.closed = False
        session.listening = True
        session.muted = False
        session.turns = asyncio.Queue()
        session.voice_client = SimpleNamespace(guild=SimpleNamespace(id=42))
        notices = []

        async def fail(_turn):
            raise SpeechModelTermsRequired("orpheus", operation="tts")

        async def notice(error):
            notices.append(error)
            session.closed = True

        session._answer_turn = fail
        session._notice_speech_access_error = notice
        session.turns.put_nowait(Utterance(1, "Speaker", b"pcm"))

        await session._worker_loop()

        assert session.listening is True
        assert session.muted is False
        assert len(notices) == 1

    asyncio.run(scenario())


def test_tts_access_failure_posts_generated_text_fallback(monkeypatch):
    from commands.voice import VoiceSession, engine
    from media.voice_buffer import Utterance
    from utils.settings import settings

    async def scenario():
        class DeniedSpeech:
            async def transcribe(self, _pcm):
                return "What time is it?"

            async def synthesize(self, _text):
                raise SpeechModelTermsRequired("orpheus", operation="tts")

        class Channel:
            def __init__(self):
                self.messages = []

            async def send(self, content, **_kwargs):
                self.messages.append(content)

        async def respond(**_kwargs):
            return {"raw": "It is 10:30 UTC."}

        monkeypatch.setattr(settings, "voice_transcripts", False)
        monkeypatch.setattr(settings, "voice_tts_text_fallback", True)
        monkeypatch.setattr(engine, "respond", respond)
        session = object.__new__(VoiceSession)
        session.speech = DeniedSpeech()
        session.transcript_guard = SimpleNamespace(is_duplicate=lambda *_args: False)
        session.text_channel = Channel()

        with pytest.raises(SpeechModelTermsRequired):
            await session._answer_turn(Utterance(1, "Speaker", b"pcm"))

        assert len(session.text_channel.messages) == 1
        assert "What time is it?" in session.text_channel.messages[0]
        assert "It is 10:30 UTC." in session.text_channel.messages[0]

    asyncio.run(scenario())


def test_tts_access_warning_is_not_spammed_for_the_same_failure(monkeypatch):
    from commands.voice import VoiceSession

    async def scenario():
        session = object.__new__(VoiceSession)
        session.tts_available = None
        session.speech_access_notice_key = None
        messages = []

        async def notice(message):
            messages.append(message)

        session._notice = notice
        error = SpeechModelTermsRequired("orpheus", operation="tts")
        await session._notice_speech_access_error(error)
        await session._notice_speech_access_error(error)

        assert session.tts_available is False
        assert len(messages) == 1
        assert "Listening remains active" in messages[0]

    asyncio.run(scenario())


def test_immediate_lavalink_failure_cancels_pending_now_playing(monkeypatch):
    from commands.music import MusicCommands

    async def scenario():
        bot = SimpleNamespace(get_channel=lambda _channel_id: None)
        cog = MusicCommands(bot)
        guild = SimpleNamespace(id=77)
        node = SimpleNamespace(identifier="nexus-main")
        track = FakeTrack("failed")
        player = SimpleNamespace(
            guild=guild,
            node=node,
            current=track,
            queue=wavelink.Queue(),
        )
        pending = asyncio.create_task(asyncio.sleep(30))
        cog.announcement_tasks[guild.id] = ("youtube:failed", pending)
        notices = []

        async def no_fallback(_player, _track):
            return None

        async def record_notice(guild_id, track_key, message):
            notices.append((guild_id, track_key, message))

        monkeypatch.setattr(cog, "try_spotify_fallback", no_fallback)
        monkeypatch.setattr(cog, "send_failure_notice", record_notice)
        payload = SimpleNamespace(
            player=player,
            track=track,
            exception={
                "message": "source failed",
                "severity": "fault",
                "cause": "403",
            },
        )

        await cog.on_wavelink_track_exception(payload)
        await asyncio.sleep(0)

        assert pending.cancelled()
        assert len(notices) == 1
        assert "skipping" in notices[0][2].casefold()

    asyncio.run(scenario())


def test_failed_loop_track_advances_once_then_restores_loop_mode(monkeypatch):
    from commands.music import MusicCommands

    async def scenario():
        bot = SimpleNamespace(get_channel=lambda _channel_id: None)
        cog = MusicCommands(bot)
        guild = SimpleNamespace(id=78, voice_client=None)
        node = SimpleNamespace(identifier="nexus-main")
        failed = FakeTrack("failed-loop")
        queue = wavelink.Queue()
        queue.mode = wavelink.QueueMode.loop
        player = SimpleNamespace(
            guild=guild,
            node=node,
            current=failed,
            queue=queue,
            connected=True,
        )
        guild.voice_client = player

        async def no_fallback(_player, _track):
            return None

        async def no_notice(_guild_id, _track_key, _message):
            return None

        monkeypatch.setattr(cog, "try_spotify_fallback", no_fallback)
        monkeypatch.setattr(cog, "send_failure_notice", no_notice)
        monkeypatch.setattr(cog, "schedule_failed_track_advance", lambda *_args: None)

        await cog.on_wavelink_track_exception(
            SimpleNamespace(
                player=player,
                track=failed,
                exception={
                    "message": "source failed",
                    "severity": "fault",
                    "cause": "403",
                },
            )
        )
        assert queue.mode is wavelink.QueueMode.normal
        assert cog.loop_modes_to_restore[guild.id] is wavelink.QueueMode.loop

        replacement = FakeTrack("working")
        player.current = replacement
        await cog.on_wavelink_track_start(
            SimpleNamespace(player=player, track=replacement)
        )
        assert queue.mode is wavelink.QueueMode.loop
        assert guild.id not in cog.loop_modes_to_restore

        cog.cancel_pending_announcement(guild.id)
        cog.release_guild(guild.id)

    asyncio.run(scenario())


def test_shared_audio_coordinator_keeps_one_mode_per_guild():
    async def scenario():
        coordinator = GuildAudioCoordinator()
        async with coordinator.lock_for(9):
            coordinator.claim(9, "music")
        assert coordinator.state_for(9).mode == "music"

        coordinator.set_tts_speaking(9, True)
        assert coordinator.state_for(9).tts_speaking is False

        async with coordinator.lock_for(9):
            coordinator.claim(9, "voice")
            coordinator.set_tts_speaking(9, True)
        assert coordinator.state_for(9).mode == "voice"
        assert coordinator.state_for(9).tts_speaking is True

        coordinator.release(9, "music")
        assert coordinator.state_for(9).mode == "voice"
        coordinator.release(9, "voice")
        assert coordinator.state_for(9).mode is None
        assert coordinator.state_for(9).tts_speaking is False

    asyncio.run(scenario())
