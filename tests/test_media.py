"""Offline tests for music formatting and live-voice buffering."""

import io
import wave

import pytest

from media.common import format_duration, parse_timecode, speakable_text
from media.speech import pcm_to_wav
from media.voice_buffer import PCM_BYTES_PER_SECOND, UtteranceBuffer


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("90", 90_000),
        ("1:30", 90_000),
        ("1:02:03", 3_723_000),
        ("1h2m3s", 3_723_000),
    ],
)
def test_timecodes_are_player_ready(value, expected):
    assert parse_timecode(value) == expected


def test_invalid_timecode_is_rejected():
    with pytest.raises(ValueError):
        parse_timecode("tomorrow")


def test_durations_cover_streams_and_long_tracks():
    assert format_duration(90_000) == "1:30"
    assert format_duration(3_723_000) == "1:02:03"
    assert format_duration(None, stream=True) == "LIVE"


def test_voice_text_does_not_read_code_or_urls_aloud():
    text = "Here you go:\n```python\nprint('hello')\n```\nSee https://example.com/docs"
    spoken = speakable_text(text)

    assert "print" not in spoken
    assert "https://" not in spoken
    assert "text channel" in spoken


def test_voice_text_respects_orpheus_input_limit():
    spoken = speakable_text("word " * 100, limit=190)

    assert 1 <= len(spoken) <= 190


def test_pcm_is_wrapped_as_discord_format_wav():
    pcm = b"\x00\x00" * 2 * 960
    wrapped = pcm_to_wav(pcm)

    with wave.open(io.BytesIO(wrapped), "rb") as audio:
        assert audio.getframerate() == 48_000
        assert audio.getnchannels() == 2
        assert audio.getsampwidth() == 2
        assert audio.readframes(audio.getnframes()) == pcm


def test_utterance_closes_after_silence():
    buffer = UtteranceBuffer(
        silence_seconds=0.8,
        minimum_seconds=0.5,
        maximum_seconds=20,
    )
    pcm = b"x" * int(PCM_BYTES_PER_SECOND * 0.6)

    buffer.feed(42, "Speaker", pcm, now=10.0)

    assert buffer.drain_ready(now=10.5) == []

    ready = buffer.drain_ready(now=10.9)

    assert len(ready) == 1
    assert ready[0].user_id == 42
    assert ready[0].display_name == "Speaker"
    assert ready[0].pcm == pcm


def test_short_packet_noise_is_dropped():
    buffer = UtteranceBuffer(
        silence_seconds=0.5,
        minimum_seconds=0.5,
        maximum_seconds=20,
    )
    buffer.feed(42, "Speaker", b"x" * 1000, now=1.0)

    assert buffer.drain_ready(now=2.0) == []


def test_maximum_turn_is_bounded():
    buffer = UtteranceBuffer(
        silence_seconds=1,
        minimum_seconds=0.1,
        maximum_seconds=1,
    )
    buffer.feed(7, "Long speaker", b"x" * (PCM_BYTES_PER_SECOND * 2), now=1.0)

    ready = buffer.drain_ready(now=1.0)

    assert len(ready) == 1
    assert len(ready[0].pcm) == PCM_BYTES_PER_SECOND


def test_simultaneous_speaker_buffers_are_bounded():
    buffer = UtteranceBuffer(
        silence_seconds=1,
        minimum_seconds=0.1,
        maximum_seconds=2,
        max_speakers=2,
    )
    packet = b"x" * int(PCM_BYTES_PER_SECOND * 0.2)

    buffer.feed(1, "One", packet, now=1.0)
    buffer.feed(2, "Two", packet, now=1.0)
    buffer.feed(3, "Dropped", packet, now=1.0)

    ready = buffer.drain_ready(now=3.0)

    assert {turn.user_id for turn in ready} == {1, 2}


def test_command_surface_is_complete_but_has_no_download_or_lyrics_command():
    from commands.music import MusicCommands

    names = {command.name for command in MusicCommands.music.commands}

    assert {
        "play",
        "playnext",
        "pause",
        "resume",
        "skip",
        "previous",
        "queue",
        "jump",
        "loop",
        "autoplay",
        "filter",
        "disconnect",
    } <= names
    assert "download" not in names
    assert "lyrics" not in names


def test_voice_receive_has_dave_compatibility():
    from commands.voice import DAVE_COMPATIBILITY
    from discord.ext.voice_recv.opus import PacketDecoder

    assert DAVE_COMPATIBILITY.ready is True
    assert getattr(PacketDecoder, "_nexus_dave_compatible", False) or hasattr(
        PacketDecoder, "_dave_decrypt"
    )
