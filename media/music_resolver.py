"""Pure helpers for Lavalink capability checks and stable music resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse


SPOTIFY_KINDS = frozenset({"track", "album", "playlist"})
YOUTUBE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
)


@dataclass(frozen=True, slots=True)
class SpotifyRequest:
    kind: str
    identifier: str


@dataclass(frozen=True, slots=True)
class PluginCapability:
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class NodeCapabilities:
    """Features reported by Lavalink's authenticated ``/v4/info`` endpoint."""

    identifier: str
    probed: bool
    source_managers: tuple[str, ...] = ()
    plugins: tuple[PluginCapability, ...] = ()
    error: str | None = None

    @property
    def lavasrc_loaded(self) -> bool:
        return any("lavasrc" in plugin.name.casefold() for plugin in self.plugins)

    @property
    def spotify_available(self) -> bool:
        return self.lavasrc_loaded and "spotify" in self.source_managers

    @property
    def youtube_plugin_loaded(self) -> bool:
        return any("youtube" in plugin.name.casefold() for plugin in self.plugins)

    @property
    def youtube_available(self) -> bool:
        return "youtube" in self.source_managers

    @classmethod
    def unknown(cls, identifier: str, error: str | None = None) -> "NodeCapabilities":
        return cls(identifier=identifier, probed=False, error=error)

    @classmethod
    def from_info(cls, identifier: str, info: Any) -> "NodeCapabilities":
        sources = _value(info, "source_managers", "sourceManagers") or ()
        plugins = _value(info, "plugins") or ()
        parsed_plugins: list[PluginCapability] = []
        for plugin in plugins:
            name = str(_value(plugin, "name") or "unknown")
            version = str(_value(plugin, "version") or "unknown")
            parsed_plugins.append(PluginCapability(name=name, version=version))

        return cls(
            identifier=identifier,
            probed=True,
            source_managers=tuple(sorted({str(source).casefold() for source in sources})),
            plugins=tuple(parsed_plugins),
        )


@dataclass(frozen=True, slots=True)
class LavalinkFailure:
    message: str
    severity: str
    cause: str

    @classmethod
    def from_exception(cls, exception: Any) -> "LavalinkFailure":
        return cls(
            message=str(_value(exception, "message") or exception or "unknown"),
            severity=str(_value(exception, "severity") or "unknown"),
            cause=str(_value(exception, "cause") or "unknown"),
        )


def _value(value: Any, *names: str) -> Any:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
        return None
    for name in names:
        found = getattr(value, name, None)
        if found is not None:
            return found
    return None


def parse_spotify_request(query: str) -> SpotifyRequest | None:
    """Recognize Spotify track/album/playlist URLs and canonical URIs."""
    value = query.strip()
    if value.casefold().startswith("spotify:"):
        parts = value.split(":", 2)
        if len(parts) == 3 and parts[1].casefold() in SPOTIFY_KINDS and parts[2]:
            return SpotifyRequest(parts[1].casefold(), parts[2].split("?", 1)[0])
        return None

    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()
    if host not in {"open.spotify.com", "www.open.spotify.com"}:
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].casefold().startswith("intl-"):
        parts.pop(0)
    if len(parts) < 2 or parts[0].casefold() not in SPOTIFY_KINDS:
        return None
    return SpotifyRequest(parts[0].casefold(), parts[1])


def is_youtube_url(query: str) -> bool:
    parsed = urlparse(query.strip())
    return (parsed.hostname or "").casefold() in YOUTUBE_HOSTS


def extra_value(track: Any, name: str, default: Any = None) -> Any:
    extras = getattr(track, "extras", None)
    value = _value(extras, name) if extras is not None else None
    return default if value is None else value


def track_source_name(track: Any) -> str:
    source = getattr(track, "source", None)
    if source is not None:
        source = getattr(source, "value", source)
        return str(source).casefold()

    raw = getattr(track, "raw_data", None) or getattr(track, "_raw_data", None)
    info = _value(raw, "info") or {}
    return str(_value(info, "sourceName", "source_name") or "unknown").casefold()


def track_identity(track: Any) -> str:
    """Return a stable key for dedupe/retry guards without decoding audio data."""
    source = track_source_name(track)
    identifier = getattr(track, "identifier", None)
    identifier = identifier or getattr(track, "encoded", None)
    identifier = identifier or getattr(track, "uri", None)
    identifier = identifier or f"{getattr(track, 'title', '')}|{getattr(track, 'author', '')}"
    return f"{source}:{identifier}"


def dedupe_tracks(tracks: Iterable[Any]) -> list[Any]:
    """Preserve resolver order while dropping repeated retry results."""
    result: list[Any] = []
    seen: set[str] = set()
    for track in tracks:
        identity = track_identity(track)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(track)
    return result


def select_fallback_track(candidates: Iterable[Any], failed_track: Any) -> Any | None:
    """Prefer a different playable while retaining resolver order."""
    unique = dedupe_tracks(candidates)
    if not unique:
        return None
    failed_key = track_identity(failed_track)
    return next(
        (track for track in unique if track_identity(track) != failed_key),
        unique[0],
    )


def fallback_search_query(track: Any) -> str:
    """Build a metadata-only YouTube search for a failed mirrored track."""
    title = str(getattr(track, "title", "") or "").strip()
    author = str(getattr(track, "author", "") or "").strip()
    if author.casefold().endswith(" - topic"):
        author = author[:-8].strip()
    return " ".join(part for part in (title, author) if part)[:500]
