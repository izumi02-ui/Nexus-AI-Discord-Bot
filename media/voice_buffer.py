"""Thread-safe, bounded utterance segmentation for Discord PCM audio."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass

PCM_BYTES_PER_SECOND = 48_000 * 2 * 2  # 48 kHz, signed 16-bit, stereo


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
    last_packet: float


class UtteranceBuffer:
    """Collect packets per speaker and emit a turn after a silence gap."""

    def __init__(
        self,
        *,
        silence_seconds: float,
        minimum_seconds: float,
        maximum_seconds: float,
        max_ready: int = 8,
        max_speakers: int = 8,
    ):
        self.silence_seconds = silence_seconds
        self.minimum_bytes = int(minimum_seconds * PCM_BYTES_PER_SECOND)
        self.maximum_bytes = int(maximum_seconds * PCM_BYTES_PER_SECOND)
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

        with self._lock:
            current = self._open.get(user_id)

            if current is None:
                if len(self._open) >= self.max_speakers:
                    return
                current = _OpenUtterance(display_name, [], 0, stamp)
                self._open[user_id] = current

            current.display_name = display_name
            current.chunks.append(bytes(pcm))
            current.size += len(pcm)
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

        if current is None or current.size < self.minimum_bytes:
            return

        self._ready.append(
            Utterance(
                user_id=user_id,
                display_name=current.display_name,
                pcm=b"".join(current.chunks)[: self.maximum_bytes],
            )
        )
