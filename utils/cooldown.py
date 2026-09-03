"""
Project Nexus

Cooldowns

Rate limiting for a bot that usually runs on free API tiers.

Two separate buckets matter: a user spamming the bot should not exhaust the
provider's quota for everyone, and a burst of searches should not hit the
evidence APIs' own limits. Both are per-key in-memory (no database writes on
the hot path) and fail open - if the cooldown layer breaks, the bot keeps
answering.
"""

import time
from collections import defaultdict

from utils.logger import logger

DEFAULTS = {
    "ask": (8.0, 30.0),        # (per-message spacing, burst recovery)
    "search": (15.0, 60.0),
    "admin": (1.0, 1.0),
    "refresh": (120.0, 120.0),
}


class CooldownManager:

    def __init__(self):
        self._last: dict[tuple[str, int], float] = {}
        self._blocked = defaultdict(int)

    def remaining(self, action: str, key: int) -> float:
        spacing, _ = DEFAULTS.get(action, (5.0, 15.0))

        last = self._last.get((action, key))

        if last is None:
            return 0.0

        return max(0.0, spacing - (time.monotonic() - last))

    def allow(self, action: str, key: int) -> bool:
        """True when this action may run now; records the timestamp if so."""
        try:
            if remaining := self.remaining(action, key):
                self._blocked[(action, key)] += 1

                logger.debug(
                    "Cooldown active for %s/%s: %.1fs left",
                    action,
                    key,
                    remaining,
                )

                return False

            self._last[(action, key)] = time.monotonic()

            return True
        except Exception as error:  # noqa: BLE001 - never deny service on a bug
            logger.debug("Cooldown check failed: %s", error)

            return True

    def message(self, action: str, key: int) -> str:
        remaining = self.remaining(action, key)

        if remaining <= 0:
            return ""

        if remaining < 3:
            return f"⏳ One moment - try again in {remaining:.0f}s."

        return f"⏳ That is quick for now. You can ask again in {remaining:.0f} seconds."

    def reset(self, key: int | None = None, action: str | None = None):
        if key is None:
            self._last.clear()

            return

        for (stored_action, stored_key) in list(self._last):
            if stored_key == key and (action is None or stored_action == action):
                self._last.pop((stored_action, stored_key), None)

    def stats(self) -> dict:
        return {
            "tracked": len(self._last),
            "blocked": sum(self._blocked.values()),
        }


cooldown = CooldownManager()
