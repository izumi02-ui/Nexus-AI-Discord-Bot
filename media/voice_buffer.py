"""Thread-safe, bounded utterance segmentation for Discord PCM audio."""

from __future__ import annotations

import math
import re
import sys
import threading
import time
from array import array
from collections import deque
from dataclasses import dataclass

PCM_BYTES_PER_SECOND = 48_000 * 2 * 2  # 48 kHz, signed 16-bit, stereo


def pcm_rms(pcm: bytes | None) -> int:
    """Return a lightweight RMS level for little-endian signed 16-bit PCM.

    Discord supplies 48 kHz stereo frames. Sampling every fourth value keeps
    the receive-thread work small while still separating real speech from the
    zero/near-zero frames Discord sends while a member is silent.
    """
    if not pcm:
        return 0

    usable = len(pcm) - (len(pcm) % 2)
    if usable <= 0:
        return 0

    samples = array("h")
    samples.frombytes(pcm[:usable])
    if sys.byteorder != "little":
        samples.byteswap()

    sampled = samples[::4]
    if not sampled:
        return 0

    mean_square = sum(int(sample) * int(sample) for sample in sampled) // len(sampled)
    return math.isqrt(mean_square)


@dataclass(slots=True)
class Utterance:
    user_id: int
    display_name: str
    pcm: bytes

    @property
    def seconds(self) -> float:
        return len(self.pcm) / PCM_BYTES_PER_SECOND


@dataclass(slots=True)
class _OpenUtterance:
    display_name: str
    chunks: list[bytes]
    size: int
    voiced_size: int
    last_packet: float


class DuplicateTranscriptGuard:
    """Reject an identical normalized transcript repeated by one speaker."""

    def __init__(self, *, window_seconds: float, max_entries: int = 256):
        self.window_seconds = max(0.0, window_seconds)
        self.max_entries = max(1, max_entries)
        self._recent: dict[int, tuple[str, float]] = {}

    @staticmethod
    def normalize(text: str) -> str:
        return " ".join(re.sub(r"[^\w]+", " ", text.casefold()).split())

    def is_duplicate(
        self,
        user_id: int,
        text: str,
        *,
        now: float | None = None,
    ) -> bool:
        key = self.normalize(text)
        if not key or self.window_seconds <= 0:
            return False

        stamp = time.monotonic() if now is None else now
        previous = self._recent.get(user_id)
        self._recent[user_id] = (key, stamp)

        if len(self._recent) > self.max_entries:
            oldest = min(self._recent, key=lambda item: self._recent[item][1])
            self._recent.pop(oldest, None)

        return bool(
            previous
            and previous[0] == key
            and stamp - previous[1] < self.window_seconds
        )

    def clear(self) -> None:
        self._recent.clear()


class UtteranceBuffer:
    """Collect packets per speaker and emit a turn after a silence gap."""

    def __init__(
        self,
        *,
        silence_seconds: float,
        minimum_seconds: float,
        maximum_seconds: float,
        minimum_rms: int = 250,
        max_ready: int = 8,
        max_speakers: int = 8,
    ):
        self.silence_seconds = silence_seconds
        self.minimum_bytes = int(minimum_seconds * PCM_BYTES_PER_SECOND)
        self.maximum_bytes = int(maximum_seconds * PCM_BYTES_PER_SECOND)
        self.minimum_rms = max(0, min(32_767, int(minimum_rms)))
        self.max_ready = max(1, max_ready)
        self.max_speakers = max(1, max_speakers)
        self._open: dict[int, _OpenUtterance] = {}
        self._ready: deque[Utterance] = deque(maxlen=self.max_ready)
        self._lock = threading.Lock()

    def feed(
        self,
        user_id: int,
        display_name: str,
        pcm: bytes | None,
        *,
        now: float | None = None,
    ) -> None:
        if not pcm:
            return

        stamp = time.monotonic() if now is None else now
        packet = bytes(pcm)
        voiced = pcm_rms(packet) >= self.minimum_rms

        with self._lock:
            current = self._open.get(user_id)

            # Do not open an utterance for Discord's silence/keepalive frames.
            # A little trailing silence is retained after real speech so the
            # transcription stays natural, but it does not count toward the
            # minimum voiced duration or extend the end-of-turn timer.
            if not voiced:
                if (
                    current is not None
                    and stamp - current.last_packet < self.silence_seconds
                    and current.size < self.maximum_bytes
                ):
                    remaining = self.maximum_bytes - current.size
                    chunk = packet[:remaining]
                    current.chunks.append(chunk)
                    current.size += len(chunk)
                return

            if current is None:
                if len(self._open) >= self.max_speakers:
                    return
                current = _OpenUtterance(display_name, [], 0, 0, stamp)
                self._open[user_id] = current

            current.display_name = display_name
            remaining = self.maximum_bytes - current.size
            chunk = packet[:remaining]
            current.chunks.append(chunk)
            current.size += len(chunk)
            current.voiced_size += len(chunk)
            current.last_packet = stamp

            if current.size >= self.maximum_bytes:
                self._finish_locked(user_id)

    def drain_ready(self, *, now: float | None = None) -> list[Utterance]:
        """Close silent speakers and return all completed turns."""
        stamp = time.monotonic() if now is None else now

        with self._lock:
            expired = [
                user_id
                for user_id, current in self._open.items()
                if stamp - current.last_packet >= self.silence_seconds
            ]

            for user_id in expired:
                self._finish_locked(user_id)

            rows = list(self._ready)
            self._ready.clear()

        return rows

    def clear(self) -> None:
        with self._lock:
            self._open.clear()
            self._ready.clear()

    def _finish_locked(self, user_id: int) -> None:
        current = self._open.pop(user_id, None)

        if current is None or current.voiced_size < self.minimum_bytes:
            return

        self._ready.append(
            Utterance(
                user_id=user_id,
                display_name=current.display_name,
                pcm=b"".join(current.chunks)[: self.maximum_bytes],
            )
        )
