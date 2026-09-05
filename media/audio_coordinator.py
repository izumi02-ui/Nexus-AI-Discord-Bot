"""Shared per-guild ownership for Nexus voice connections.

Discord allows one voice protocol per bot account in a guild. Music uses a
Wavelink/Lavalink player while live conversation uses a VoiceRecvClient, so the
two modes must perform an atomic handoff instead of opening competing clients.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal


AudioMode = Literal["music", "voice"]


@dataclass(slots=True)
class GuildAudioState:
    """Small shared state; the Wavelink player remains the music queue owner."""

    mode: AudioMode | None = None
    tts_speaking: bool = False


class GuildAudioCoordinator:
    """Serialize voice-mode changes and expose one state object per guild."""

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}
        self._states: dict[int, GuildAudioState] = {}

    def lock_for(self, guild_id: int) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())

    def state_for(self, guild_id: int) -> GuildAudioState:
        return self._states.setdefault(guild_id, GuildAudioState())

    def claim(self, guild_id: int, mode: AudioMode) -> GuildAudioState:
        state = self.state_for(guild_id)
        state.mode = mode
        if mode != "voice":
            state.tts_speaking = False
        return state

    def release(self, guild_id: int, mode: AudioMode) -> None:
        state = self._states.get(guild_id)
        if state is None or state.mode != mode:
            return
        state.mode = None
        state.tts_speaking = False

    def set_tts_speaking(self, guild_id: int, speaking: bool) -> None:
        state = self.state_for(guild_id)
        if state.mode == "voice":
            state.tts_speaking = speaking

    def cleanup(self, guild_id: int) -> None:
        self._states.pop(guild_id, None)
        lock = self._locks.get(guild_id)
        if lock is not None and not lock.locked():
            self._locks.pop(guild_id, None)


audio_coordinator = GuildAudioCoordinator()
