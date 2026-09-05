"""Production Lavalink music controls for Project Nexus (Nexy)."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections import defaultdict

import discord
import wavelink
from discord import app_commands
from discord.ext import commands

from media.audio_coordinator import audio_coordinator
from media.common import format_duration, markdown_link, truncate
from media.music_resolver import (
    LavalinkFailure,
    NodeCapabilities,
    dedupe_tracks,
    extra_value,
    fallback_search_query,
    is_youtube_url,
    parse_spotify_request,
    select_fallback_track,
    track_identity,
    track_source_name,
)
from utils.logger import logger
from utils.permissions import is_admin
from utils.settings import settings


MUSIC_COLOUR = discord.Colour.from_rgb(88, 101, 242)


class MusicError(RuntimeError):
    """A user-actionable music error."""


def requester_name(track: wavelink.Playable) -> str:
    extras = getattr(track, "extras", None)
    return getattr(extras, "requester_name", "Unknown") if extras else "Unknown"


def track_line(track: wavelink.Playable, index: int | None = None) -> str:
    prefix = f"`{index:02d}.` " if index is not None else ""
    duration = format_duration(track.length, stream=track.is_stream)
    return (
        f"{prefix}{markdown_link(track.title, track.uri)}"
        f" — `{duration}` · {truncate(track.author or 'Unknown artist', 50)}"
    )


class MusicControls(discord.ui.View):
    """Short-lived controls attached to now-playing messages."""

    def __init__(self, cog: "MusicCommands", guild_id: int):
        super().__init__(timeout=900)
        self.cog = cog
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        player = guild.voice_client if guild else None

        if not isinstance(player, wavelink.Player) or not player.connected:
            await interaction.response.send_message(
                "Nothing is playing in this server.", ephemeral=True
            )
            return False

        try:
            self.cog.ensure_same_channel(interaction, player)
        except MusicError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return False

        return True

    @discord.ui.button(label="Pause / Resume", emoji="⏯️", style=discord.ButtonStyle.primary)
    async def pause_resume(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        player = interaction.guild.voice_client
        await player.pause(not player.paused)
        await interaction.response.send_message(
            "Resumed." if not player.paused else "Paused.", ephemeral=True
        )

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = interaction.guild.voice_client
        skipped = player.current
        await player.skip(force=True)
        await interaction.response.send_message(
            f"Skipped **{truncate(skipped.title, 70)}**." if skipped else "Nothing to skip.",
            ephemeral=True,
        )

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.secondary)
    async def stop(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = interaction.guild.voice_client
        player.queue.clear()
        await player.skip(force=True)
        await interaction.response.send_message("Playback stopped and queue cleared.", ephemeral=True)

    @discord.ui.button(label="Leave", emoji="👋", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, _button: discord.ui.Button):
        player = interaction.guild.voice_client
        self.cog.clear_player(player)
        await player.disconnect()
        self.cog.release_guild(interaction.guild_id)
        await interaction.response.send_message("Disconnected from voice.", ephemeral=True)


class MusicCommands(commands.Cog):
    """Queue, playback, looping, filters, and interactive controls."""

    music = app_commands.Group(
        name="music",
        description="Nexy music player commands.",
        guild_only=True,
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.node_error: str | None = None
        self.announce_channels: dict[int, int] = {}
        self.locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.node_capabilities: dict[str, NodeCapabilities] = {}
        self.announcement_tasks: dict[int, tuple[str, asyncio.Task]] = {}
        self.failure_advance_tasks: dict[int, tuple[str, asyncio.Task]] = {}
        self.fallback_attempts: defaultdict[int, set[str]] = defaultdict(set)
        self.last_failure_notice: dict[int, tuple[str, float]] = {}
        self.loop_modes_to_restore: dict[int, wavelink.QueueMode] = {}

    async def cog_load(self):
        if not settings.music_enabled:
            self.node_error = "Music is disabled by MUSIC_ENABLED."
            logger.info("Music commands loaded but disabled by configuration.")
            return

        if not settings.lavalink_uri or not settings.lavalink_password:
            self.node_error = "LAVALINK_URI and LAVALINK_PASSWORD are not configured."
            logger.info("Music commands loaded; Lavalink is not configured.")
            return

        try:
            node = wavelink.Node(
                uri=settings.lavalink_uri,
                password=settings.lavalink_password,
                identifier=settings.lavalink_identifier,
                inactive_player_timeout=settings.lavalink_inactive_timeout,
                retries=5,
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
            await self.refresh_node_capabilities(node)
            self.node_error = None
            logger.info("Lavalink node %s connected.", settings.lavalink_identifier)
        except Exception as error:  # noqa: BLE001 - chat must still start
            self.node_error = str(error)
            logger.warning("Lavalink unavailable: %s", error)

    async def cog_unload(self):
        for _track_key, task in self.announcement_tasks.values():
            task.cancel()
        self.announcement_tasks.clear()
        for _track_key, task in self.failure_advance_tasks.values():
            task.cancel()
        self.failure_advance_tasks.clear()
        for guild_id in list(self.announce_channels):
            self.release_guild(guild_id)
        try:
            await wavelink.Pool.close()
        except Exception:  # noqa: BLE001
            pass

    def health(self) -> dict:
        nodes = list(wavelink.Pool.nodes.values())
        ready = any(node.status is wavelink.NodeStatus.CONNECTED for node in nodes)
        capabilities = self._preferred_capabilities(nodes)
        return {
            "enabled": settings.music_enabled,
            "configured": bool(settings.lavalink_uri and settings.lavalink_password),
            "ready": ready,
            "nodes": len(nodes),
            "players": sum(len(node.players) for node in nodes),
            "capabilities_probed": capabilities.probed,
            "lavasrc_loaded": capabilities.lavasrc_loaded if capabilities.probed else None,
            "spotify_source": capabilities.spotify_available if capabilities.probed else None,
            "youtube_plugin": (
                capabilities.youtube_plugin_loaded if capabilities.probed else None
            ),
            "youtube_source": capabilities.youtube_available if capabilities.probed else None,
            "plugins": [
                f"{plugin.name}:{plugin.version}" for plugin in capabilities.plugins
            ],
            "capability_error": capabilities.error,
            "error": self.node_error,
        }

    @staticmethod
    def _node_identifier(node) -> str:
        return str(getattr(node, "identifier", settings.lavalink_identifier))

    def _preferred_capabilities(self, nodes=None) -> NodeCapabilities:
        nodes = nodes if nodes is not None else list(wavelink.Pool.nodes.values())
        for node in nodes:
            identifier = self._node_identifier(node)
            capabilities = self.node_capabilities.get(identifier)
            if capabilities is not None and capabilities.probed:
                return capabilities
        if nodes:
            identifier = self._node_identifier(nodes[0])
            return self.node_capabilities.get(
                identifier, NodeCapabilities.unknown(identifier)
            )
        return NodeCapabilities.unknown(settings.lavalink_identifier, self.node_error)

    def capabilities_for(self, node) -> NodeCapabilities:
        identifier = self._node_identifier(node)
        return self.node_capabilities.get(
            identifier, NodeCapabilities.unknown(identifier)
        )

    async def refresh_node_capabilities(self, node) -> NodeCapabilities:
        """Read authenticated Lavalink info without logging credentials."""
        identifier = self._node_identifier(node)
        try:
            info = await asyncio.wait_for(
                node.fetch_info(),
                timeout=settings.music_node_probe_timeout,
            )
            capabilities = NodeCapabilities.from_info(identifier, info)
        except Exception as error:  # noqa: BLE001 - diagnostics must not stop music startup
            capabilities = NodeCapabilities.unknown(identifier, str(error)[:500])
            logger.warning(
                "Could not inspect Lavalink node capabilities node=%s error_type=%s error=%s",
                identifier,
                type(error).__name__,
                str(error)[:500],
            )
        self.node_capabilities[identifier] = capabilities

        if capabilities.probed:
            plugins = ", ".join(
                f"{plugin.name}:{plugin.version}" for plugin in capabilities.plugins
            ) or "none"
            sources = ", ".join(capabilities.source_managers) or "none"
            logger.info(
                "Lavalink capabilities node=%s plugins=%s sources=%s",
                identifier,
                plugins,
                sources,
            )
            if not capabilities.youtube_plugin_loaded:
                logger.warning(
                    "Lavalink node %s does not report the modern YouTube plugin.",
                    identifier,
                )
            if not capabilities.spotify_available:
                logger.warning(
                    "Lavalink node %s does not report LavaSrc Spotify support.",
                    identifier,
                )
        return capabilities

    def ensure_ready(self) -> None:
        if not settings.music_enabled:
            raise MusicError("Music is disabled on this Nexus instance.")

        connected = any(
            node.status is wavelink.NodeStatus.CONNECTED
            for node in wavelink.Pool.nodes.values()
        )
        if connected:
            self.node_error = None
            return

        if self.node_error:
            raise MusicError(f"Music is not ready: {self.node_error}")

        if not connected:
            raise MusicError("The Lavalink node is reconnecting. Try again in a moment.")

    def user_channel(self, interaction: discord.Interaction):
        member = interaction.user
        state = getattr(member, "voice", None)

        if state is None or state.channel is None:
            raise MusicError("Join a voice channel first.")

        return state.channel

    def ensure_same_channel(
        self, interaction: discord.Interaction, player: wavelink.Player
    ) -> None:
        channel = self.user_channel(interaction)

        roles = getattr(interaction.user, "roles", ())
        is_dj = bool(settings.music_dj_role) and any(
            role.name.casefold() == settings.music_dj_role.casefold() for role in roles
        )
        if player.channel.id != channel.id and not (is_admin(interaction.user) or is_dj):
            raise MusicError(f"Join {player.channel.mention} to control this player.")

    def player(self, interaction: discord.Interaction) -> wavelink.Player:
        guild = interaction.guild
        player = guild.voice_client if guild else None

        if not isinstance(player, wavelink.Player) or not player.connected:
            raise MusicError("Nexy is not connected to a music voice channel.")

        self.ensure_same_channel(interaction, player)
        return player

    @staticmethod
    def clear_player(player: wavelink.Player) -> None:
        """Clear every session-owned queue reference before disconnecting."""
        player.queue.clear()
        player.queue.mode = wavelink.QueueMode.normal
        if player.queue.history is not None:
            player.queue.history.clear()

    def release_guild(self, guild_id: int) -> None:
        self.announce_channels.pop(guild_id, None)
        pending = self.announcement_tasks.pop(guild_id, None)
        if pending is not None:
            pending[1].cancel()
        advance = self.failure_advance_tasks.pop(guild_id, None)
        if advance is not None:
            advance[1].cancel()
        self.fallback_attempts.pop(guild_id, None)
        self.last_failure_notice.pop(guild_id, None)
        self.loop_modes_to_restore.pop(guild_id, None)
        audio_coordinator.release(guild_id, "music")

    async def stop_guild(self, guild_id: int, *, disconnect: bool = True) -> bool:
        """Stop a guild player during explicit leave or media-mode handoff."""
        guild = self.bot.get_guild(guild_id)
        player = guild.voice_client if guild else None
        if not isinstance(player, wavelink.Player):
            self.release_guild(guild_id)
            return False

        self.clear_player(player)
        if player.current is not None and not disconnect:
            await player.skip(force=True)
        if disconnect and player.connected:
            await player.disconnect()
        self.release_guild(guild_id)
        return True

    async def connect_player(self, interaction: discord.Interaction) -> wavelink.Player:
        self.ensure_ready()
        channel = self.user_channel(interaction)
        guild = interaction.guild

        async with audio_coordinator.lock_for(guild.id):
            existing = guild.voice_client

            if isinstance(existing, wavelink.Player) and existing.connected:
                self.ensure_same_channel(interaction, existing)
                audio_coordinator.claim(guild.id, "music")
                return existing

            if existing is not None:
                # Live conversation and music use different voice protocols.
                # The shared lock makes this handoff atomic for the guild.
                voice_cog = self.bot.get_cog("VoiceCommands")
                if voice_cog is not None:
                    await voice_cog.stop_guild(guild.id, disconnect=True)
                else:
                    await existing.disconnect(force=True)

            player: wavelink.Player = await channel.connect(
                cls=wavelink.Player,
                self_deaf=True,
            )
            player.autoplay = wavelink.AutoPlayMode.partial
            await player.set_volume(settings.music_default_volume)
            audio_coordinator.claim(guild.id, "music")
            return player

    async def ensure_player_voice_ready(self, player: wavelink.Player) -> None:
        """Validate the Discord and Lavalink sides before starting a source."""
        if not player.connected or player.channel is None or player.guild is None:
            raise MusicError("The music voice connection is not ready. Rejoin and try again.")
        if player.guild.voice_client is not player:
            raise MusicError("This server's music player was replaced. Use `/music join` again.")

        state = None
        for _ in range(5):
            member = player.guild.me
            state = getattr(member, "voice", None) if member is not None else None
            if state is not None and state.channel is not None:
                break
            await asyncio.sleep(0.1)

        if state is None or state.channel is None or state.channel.id != player.channel.id:
            raise MusicError("Discord has not confirmed Nexy's voice connection yet. Try again.")
        if any(
            bool(getattr(state, field, False))
            for field in ("mute", "self_mute", "suppress")
        ):
            raise MusicError(
                "Nexy is muted or suppressed in this voice channel. Unmute the bot, "
                "then try again."
            )
        if audio_coordinator.state_for(player.guild.id).mode != "music":
            raise MusicError("Another Nexus audio mode owns this server's voice connection.")

    async def play_track(self, player: wavelink.Player, track, **kwargs) -> None:
        await self.ensure_player_voice_ready(player)
        await player.play(track, **kwargs)

    async def respond_error(self, interaction: discord.Interaction, error: Exception):
        content = f"⚠️ {str(error)[:1200]}"
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        original = getattr(error, "original", error)
        if isinstance(original, MusicError):
            await self.respond_error(interaction, original)
            return

        logger.error(
            "Music command failed: %s",
            original,
            exc_info=(type(original), original, original.__traceback__),
        )
        await self.respond_error(interaction, MusicError("Music command failed. Check Render logs."))

    async def resolve_tracks(self, player: wavelink.Player, query: str):
        """Resolve one request through the exact capabilities of its node."""
        query = query.strip()
        spotify = parse_spotify_request(query)
        capabilities = self.capabilities_for(player.node)

        if spotify and capabilities.probed and not capabilities.lavasrc_loaded:
            raise MusicError(
                f"This is a Spotify {spotify.kind} URL, but node "
                f"`{capabilities.identifier}` does not report the LavaSrc plugin. "
                "Install/configure LavaSrc on the Lavalink service and restart it."
            )
        if spotify and capabilities.probed and not capabilities.spotify_available:
            raise MusicError(
                f"LavaSrc is present, but Spotify {spotify.kind} resolution is not "
                "available. Enable `plugins.lavasrc.sources.spotify`, set both "
                "Spotify credentials on the Lavalink service, and restart it."
            )

        needs_youtube = not spotify and (
            is_youtube_url(query) or "://" not in query
        )
        if needs_youtube and capabilities.probed and not capabilities.youtube_available:
            raise MusicError(
                "The connected Lavalink node does not report a YouTube source. "
                "Load the modern `youtube-plugin`, keep built-in YouTube disabled, "
                "and restart Lavalink."
            )

        try:
            found = await wavelink.Playable.search(query, node=player.node)
        except Exception as error:  # noqa: BLE001 - convert node details to a safe message
            logger.warning(
                "Lavalink load failed node=%s request_type=%s error_type=%s error=%s",
                capabilities.identifier,
                f"spotify-{spotify.kind}" if spotify else "youtube-or-url",
                type(error).__name__,
                str(error)[:800],
            )
            if spotify:
                if not capabilities.probed:
                    raise MusicError(
                        f"The Spotify {spotify.kind} could not be resolved, and Nexus "
                        "could not confirm this node's plugins. Run `/music status`; "
                        "the Lavalink service must load LavaSrc with valid Spotify credentials."
                    ) from error
                raise MusicError(
                    f"LavaSrc is loaded, but it could not resolve this Spotify "
                    f"{spotify.kind}. Check the Lavalink service's Spotify credentials "
                    "and LavaSrc logs."
                ) from error
            if is_youtube_url(query) and capabilities.probed and not capabilities.youtube_plugin_loaded:
                raise MusicError(
                    "This YouTube URL failed and the node does not report the modern "
                    "YouTube plugin. Install/enable it and restart Lavalink."
                ) from error
            raise MusicError(
                "Lavalink could not load that source. Check `/music status` and the "
                "Lavalink source/plugin logs."
            ) from error

        if not found:
            if spotify:
                raise MusicError(
                    f"LavaSrc returned no playable matches for that Spotify {spotify.kind}."
                )
            raise MusicError("No playable tracks matched that search.")

        is_playlist = isinstance(found, wavelink.Playlist)
        tracks = dedupe_tracks(list(found) if is_playlist else [found[0]])
        if not tracks:
            raise MusicError("The resolver returned only duplicate or unusable tracks.")
        return found, is_playlist, tracks, spotify

    def add_requester(
        self,
        tracks: list[wavelink.Playable],
        user,
        *,
        origin_query: str,
        spotify_kind: str | None,
    ) -> None:
        for track in tracks:
            track.extras = {
                "requester_id": user.id,
                "requester_name": user.display_name,
                "origin_query": origin_query if spotify_kind else "",
                "origin_kind": f"spotify-{spotify_kind}" if spotify_kind else "direct",
                "fallback_attempted": False,
            }

    def now_playing_embed(
        self,
        player: wavelink.Player,
        track: wavelink.Playable | None = None,
    ) -> discord.Embed:
        track = track or player.current
        if track is None:
            return discord.Embed(description="Nothing is playing.", colour=MUSIC_COLOUR)

        embed = discord.Embed(
            title="Now Playing",
            description=track_line(track),
            colour=MUSIC_COLOUR,
            url=track.uri,
        )
        embed.add_field(name="Requested by", value=requester_name(track), inline=True)
        embed.add_field(name="Volume", value=f"{player.volume}%", inline=True)
        embed.add_field(name="Up next", value=str(player.queue.count), inline=True)
        if track.artwork and track.artwork.startswith("https://"):
            embed.set_thumbnail(url=track.artwork)
        embed.set_footer(text=f"{settings.nexus_nickname} Music • /music queue")
        return embed

    async def announce_now_playing(
        self,
        player: wavelink.Player,
        track: wavelink.Playable | None = None,
    ) -> None:
        if not settings.music_announce_tracks or player.guild is None:
            return

        channel_id = self.announce_channels.get(player.guild.id)
        channel = self.bot.get_channel(channel_id) if channel_id else None

        if channel is None:
            return

        try:
            await channel.send(
                embed=self.now_playing_embed(player, track),
                view=MusicControls(self, player.guild.id),
            )
        except discord.HTTPException as error:
            logger.warning("Could not announce track in guild %s: %s", player.guild.id, error)

    def cancel_pending_announcement(
        self,
        guild_id: int,
        track_key: str | None = None,
    ) -> None:
        pending = self.announcement_tasks.get(guild_id)
        if pending is None or (track_key is not None and pending[0] != track_key):
            return
        self.announcement_tasks.pop(guild_id, None)
        pending[1].cancel()

    async def announce_after_start(
        self,
        player: wavelink.Player,
        track: wavelink.Playable,
    ) -> None:
        """Suppress false Now Playing cards for immediate source failures."""
        guild_id = player.guild.id
        track_key = track_identity(track)
        try:
            await asyncio.sleep(settings.music_start_grace_seconds)
            current = player.current
            if (
                not player.connected
                or current is None
                or track_identity(current) != track_key
            ):
                return
            await self.announce_now_playing(player, track)
        except asyncio.CancelledError:
            return
        finally:
            pending = self.announcement_tasks.get(guild_id)
            if pending is not None and pending[0] == track_key:
                self.announcement_tasks.pop(guild_id, None)

    async def enqueue(
        self,
        interaction: discord.Interaction,
        query: str,
        *,
        next_up: bool,
    ) -> None:
        await interaction.response.defer(thinking=True)
        player = await self.connect_player(interaction)

        async with self.locks[interaction.guild_id]:
            found, is_playlist, tracks, spotify = await self.resolve_tracks(
                player, query
            )
            capacity = settings.music_max_queue - player.queue.count

            if player.current is None:
                capacity += 1

            if capacity <= 0:
                raise MusicError(f"The queue limit is {settings.music_max_queue} tracks.")

            tracks = tracks[:capacity]
            self.add_requester(
                tracks,
                interaction.user,
                origin_query=query.strip(),
                spotify_kind=spotify.kind if spotify else None,
            )
            self.announce_channels[interaction.guild_id] = interaction.channel_id

            started = None
            if player.current is None:
                started = tracks.pop(0)
                await self.play_track(
                    player,
                    started,
                    volume=settings.music_default_volume,
                    populate=player.autoplay is wavelink.AutoPlayMode.enabled,
                )

            if tracks:
                if next_up:
                    for track in reversed(tracks):
                        player.queue.put_at(0, track)
                else:
                    await player.queue.put_wait(tracks)

            if is_playlist:
                detail = (
                    f"Queued **{len(tracks) + (1 if started else 0)}** tracks from "
                    f"**{truncate(found.name, 80)}**."
                )
            else:
                chosen = started or tracks[0]
                detail = (
                    f"Loading {markdown_link(chosen.title, chosen.uri)}."
                    if started
                    else f"Queued {markdown_link(chosen.title, chosen.uri)}"
                    + (" next." if next_up else f" at position **{player.queue.count}**.")
                )

        await interaction.followup.send(detail)

    async def try_spotify_fallback(
        self,
        player: wavelink.Player,
        failed_track: wavelink.Playable,
    ) -> str | None:
        """Try one metadata-based YouTube replacement for a failed mirror."""
        if not settings.music_spotify_fallback:
            return None

        origin_kind = str(extra_value(failed_track, "origin_kind", ""))
        if not origin_kind.startswith("spotify-"):
            return None
        if bool(extra_value(failed_track, "fallback_attempted", False)):
            return None

        origin_query = str(extra_value(failed_track, "origin_query", ""))
        attempt_key = f"{origin_query}|{track_identity(failed_track)}"
        attempts = self.fallback_attempts[player.guild.id]
        if attempt_key in attempts:
            return None
        if len(attempts) >= 500:
            attempts.clear()
        attempts.add(attempt_key)

        capabilities = self.capabilities_for(player.node)
        if capabilities.probed and not capabilities.youtube_available:
            return None

        query = fallback_search_query(failed_track)
        if not query:
            return None

        try:
            found = await wavelink.Playable.search(
                query,
                source="ytsearch",
                node=player.node,
            )
            if not found:
                return None
            candidates = dedupe_tracks(
                list(found) if isinstance(found, wavelink.Playlist) else list(found)
            )
            if not candidates:
                return None

            failed_key = track_identity(failed_track)
            replacement = select_fallback_track(candidates, failed_track)
            if replacement is None:
                return None
            replacement.extras = {
                "requester_id": extra_value(failed_track, "requester_id", 0),
                "requester_name": extra_value(failed_track, "requester_name", "Unknown"),
                "origin_query": origin_query,
                "origin_kind": origin_kind,
                "fallback_attempted": True,
            }

            await self.ensure_player_voice_ready(player)
            current = player.current
            if current is None:
                await self.play_track(player, replacement)
                return "playing"

            # If the failed source has not ended yet, TrackEnd will consume this
            # first. If AutoPlay already advanced, it remains next; either way,
            # the existing queue keeps its relative order.
            player.queue.put_at(0, replacement)
            return "queued"
        except Exception as error:  # noqa: BLE001 - original queue must keep moving
            logger.warning(
                "Spotify playback fallback failed guild=%s node=%s error_type=%s error=%s",
                player.guild.id,
                self._node_identifier(player.node),
                type(error).__name__,
                str(error)[:800],
            )
            return None

    def schedule_failed_track_advance(
        self,
        player: wavelink.Player,
        failed_track: wavelink.Playable,
    ) -> None:
        """Nudge only a still-stuck failed track after Lavalink's end event window."""
        guild_id = player.guild.id
        failed_key = track_identity(failed_track)
        previous = self.failure_advance_tasks.pop(guild_id, None)
        if previous is not None:
            previous[1].cancel()

        async def advance() -> None:
            try:
                await asyncio.sleep(1)
                current = player.current
                if (
                    player.connected
                    and current is not None
                    and track_identity(current) == failed_key
                ):
                    await player.skip(force=True)
            except asyncio.CancelledError:
                return
            except Exception as error:  # noqa: BLE001 - keep event handling alive
                logger.warning(
                    "Could not advance failed track guild=%s node=%s error=%s",
                    guild_id,
                    self._node_identifier(player.node),
                    str(error)[:500],
                )
            finally:
                pending = self.failure_advance_tasks.get(guild_id)
                if pending is not None and pending[0] == failed_key:
                    self.failure_advance_tasks.pop(guild_id, None)

        task = asyncio.create_task(
            advance(),
            name=f"nexy-failed-track-{guild_id}",
        )
        self.failure_advance_tasks[guild_id] = (failed_key, task)

    async def send_failure_notice(
        self,
        guild_id: int,
        track_key: str,
        message: str,
    ) -> None:
        """Send one concise failure for duplicate Lavalink exception events."""
        now = time.monotonic()
        previous = self.last_failure_notice.get(guild_id)
        if previous is not None and previous[0] == track_key and now - previous[1] < 15:
            return
        self.last_failure_notice[guild_id] = (track_key, now)

        channel_id = self.announce_channels.get(guild_id)
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if channel is None:
            return
        with contextlib.suppress(discord.HTTPException):
            await channel.send(
                message,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @music.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction):
        player = await self.connect_player(interaction)
        self.announce_channels[interaction.guild_id] = interaction.channel_id
        await interaction.response.send_message(f"Joined {player.channel.mention}.")

    @music.command(name="play", description="Play a URL or search YouTube Music.")
    @app_commands.describe(query="Song, artist, playlist, YouTube/Spotify/HTTP URL")
    async def play(self, interaction: discord.Interaction, query: str):
        await self.enqueue(interaction, query, next_up=False)

    @music.command(name="playnext", description="Put a track or playlist at the front of queue.")
    @app_commands.describe(query="Song, artist, playlist, or URL")
    async def playnext(self, interaction: discord.Interaction, query: str):
        await self.enqueue(interaction, query, next_up=True)

    @music.command(name="pause", description="Pause the current track.")
    async def pause(self, interaction: discord.Interaction):
        player = self.player(interaction)
        if player.current is None:
            raise MusicError("Nothing is playing.")
        await player.pause(True)
        await interaction.response.send_message("Paused.")

    @music.command(name="resume", description="Resume paused playback.")
    async def resume(self, interaction: discord.Interaction):
        player = self.player(interaction)
        if player.current is None:
            raise MusicError("Nothing is playing.")
        await player.pause(False)
        await interaction.response.send_message("Resumed.")

    @music.command(name="skip", description="Skip the current track.")
    async def skip(self, interaction: discord.Interaction):
        player = self.player(interaction)
        track = player.current
        if track is None:
            raise MusicError("Nothing is playing.")
        await player.skip(force=True)
        await interaction.response.send_message(f"Skipped **{truncate(track.title, 80)}**.")

    @music.command(name="previous", description="Return to the previous track.")
    async def previous(self, interaction: discord.Interaction):
        player = self.player(interaction)
        history = player.queue.history
        if history is None or history.count < 2:
            raise MusicError("There is no previous track in this session.")

        # History includes the current track. Remove it, take the preceding
        # item, then let Player.play append that item as the new current entry.
        # This makes repeated /previous calls walk backwards instead of merely
        # restarting the same previous song.
        current = player.current
        history.delete(history.count - 1)
        target = history.get_at(history.count - 1)
        history.delete(history.count - 1)
        if current is not None:
            player.queue.put_at(0, current)
        await self.play_track(player, target, add_history=True)
        await interaction.response.send_message(f"Playing **{truncate(target.title, 80)}** again.")

    @music.command(name="replay", description="Restart the current track.")
    async def replay(self, interaction: discord.Interaction):
        player = self.player(interaction)
        if player.current is None:
            raise MusicError("Nothing is playing.")
        await player.seek(0)
        await interaction.response.send_message("Restarted the current track.")

    @music.command(name="stop", description="Stop playback and clear the queue.")
    async def stop(self, interaction: discord.Interaction):
        player = self.player(interaction)
        player.queue.clear()
        if player.current is not None:
            await player.skip(force=True)
        await interaction.response.send_message("Playback stopped and queue cleared.")

    async def disconnect_player(self, interaction: discord.Interaction):
        player = self.player(interaction)
        self.clear_player(player)
        await player.disconnect()
        self.release_guild(interaction.guild_id)
        await interaction.response.send_message("Disconnected from voice.")

    @music.command(name="disconnect", description="Leave voice and clear this session.")
    async def disconnect(self, interaction: discord.Interaction):
        await self.disconnect_player(interaction)

    @music.command(name="leave", description="Alias for /music disconnect.")
    async def leave(self, interaction: discord.Interaction):
        await self.disconnect_player(interaction)

    @music.command(name="nowplaying", description="Show the current track and controls.")
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.player(interaction)
        if player.current is None:
            raise MusicError("Nothing is playing.")
        await interaction.response.send_message(
            embed=self.now_playing_embed(player),
            view=MusicControls(self, interaction.guild_id),
        )

    @music.command(name="queue", description="Show the current track and upcoming queue.")
    @app_commands.describe(page="Queue page, 10 tracks per page")
    async def queue(self, interaction: discord.Interaction, page: app_commands.Range[int, 1, 100] = 1):
        player = self.player(interaction)
        per_page = 10
        total_pages = max(1, (player.queue.count + per_page - 1) // per_page)
        page = min(page, total_pages)
        start = (page - 1) * per_page
        tracks = player.queue[start : start + per_page]
        lines = [
            f"▶️ {track_line(player.current)}" if player.current else "Nothing is playing.",
            "",
        ]
        lines.extend(track_line(track, start + offset + 1) for offset, track in enumerate(tracks))
        if not tracks:
            lines.append("The upcoming queue is empty.")
        embed = discord.Embed(
            title=f"Music Queue · {player.queue.count} upcoming",
            description="\n".join(lines)[:4000],
            colour=MUSIC_COLOUR,
        )
        embed.set_footer(text=f"Page {page}/{total_pages} • loop: {player.queue.mode.name}")
        await interaction.response.send_message(embed=embed)

    @music.command(name="remove", description="Remove one queued track by position.")
    async def remove(self, interaction: discord.Interaction, position: app_commands.Range[int, 1, 1000]):
        player = self.player(interaction)
        if position > player.queue.count:
            raise MusicError(f"Queue has only {player.queue.count} upcoming track(s).")
        track = player.queue.get_at(position - 1)
        player.queue.delete(position - 1)
        await interaction.response.send_message(f"Removed **{truncate(track.title, 80)}**.")

    @music.command(name="move", description="Move a queued track to a new position.")
    async def move(
        self,
        interaction: discord.Interaction,
        position: app_commands.Range[int, 1, 1000],
        new_position: app_commands.Range[int, 1, 1000],
    ):
        player = self.player(interaction)
        count = player.queue.count
        if position > count or new_position > count:
            raise MusicError(f"Both positions must be between 1 and {count}.")
        track = player.queue.get_at(position - 1)
        player.queue.delete(position - 1)
        player.queue.put_at(new_position - 1, track)
        await interaction.response.send_message(
            f"Moved **{truncate(track.title, 80)}** to position **{new_position}**."
        )

    @music.command(name="jump", description="Jump directly to a queued track.")
    async def jump(self, interaction: discord.Interaction, position: app_commands.Range[int, 1, 1000]):
        player = self.player(interaction)
        if position > player.queue.count:
            raise MusicError(f"Queue has only {player.queue.count} upcoming track(s).")
        target = player.queue.get_at(position - 1)
        for _ in range(position):
            player.queue.delete(0)
        await self.play_track(player, target)
        await interaction.response.send_message(f"Jumped to **{truncate(target.title, 80)}**.")

    @music.command(name="shuffle", description="Randomize the upcoming queue.")
    async def shuffle(self, interaction: discord.Interaction):
        player = self.player(interaction)
        if player.queue.count < 2:
            raise MusicError("Add at least two upcoming tracks before shuffling.")
        player.queue.shuffle()
        await interaction.response.send_message(f"Shuffled **{player.queue.count}** tracks.")

    @music.command(name="clear", description="Clear upcoming tracks without stopping the current one.")
    async def clear(self, interaction: discord.Interaction):
        player = self.player(interaction)
        count = player.queue.count
        player.queue.clear()
        await interaction.response.send_message(f"Cleared **{count}** upcoming track(s).")

    @music.command(name="loop", description="Loop one track, the queue, or turn looping off.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value="off"),
        app_commands.Choice(name="Current track", value="track"),
        app_commands.Choice(name="Entire queue", value="queue"),
    ])
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        player = self.player(interaction)
        modes = {
            "off": wavelink.QueueMode.normal,
            "track": wavelink.QueueMode.loop,
            "queue": wavelink.QueueMode.loop_all,
        }
        player.queue.mode = modes[mode.value]
        # An explicit user choice takes precedence over a pending automatic
        # restore after a failed looped track.
        self.loop_modes_to_restore.pop(interaction.guild_id, None)
        await interaction.response.send_message(f"Loop mode set to **{mode.name}**.")

    @music.command(name="volume", description="Set playback volume from 0 to 200 percent.")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 200]):
        player = self.player(interaction)
        await player.set_volume(level)
        await interaction.response.send_message(f"Volume set to **{level}%**.")

    @music.command(name="seek", description="Seek to a time such as 90, 1:30, or 1m30s.")
    async def seek(self, interaction: discord.Interaction, time: str):
        from media.common import parse_timecode

        player = self.player(interaction)
        track = player.current
        if track is None or track.is_stream or not track.is_seekable:
            raise MusicError("The current track cannot be seeked.")
        try:
            position = parse_timecode(time)
        except ValueError as error:
            raise MusicError(str(error)) from error
        if position >= track.length:
            raise MusicError(f"Track duration is {format_duration(track.length)}.")
        await player.seek(position)
        await interaction.response.send_message(f"Moved to **{format_duration(position)}**.")

    @music.command(name="autoplay", description="Continue with related tracks after the queue ends.")
    @app_commands.choices(enabled=[
        app_commands.Choice(name="On", value="on"),
        app_commands.Choice(name="Off", value="off"),
    ])
    async def autoplay(self, interaction: discord.Interaction, enabled: app_commands.Choice[str]):
        player = self.player(interaction)
        player.autoplay = (
            wavelink.AutoPlayMode.enabled
            if enabled.value == "on"
            else wavelink.AutoPlayMode.partial
        )
        await interaction.response.send_message(f"Autoplay **{enabled.value}**.")

    @music.command(name="filter", description="Apply an audio preset or reset filters.")
    @app_commands.choices(preset=[
        app_commands.Choice(name="Off", value="off"),
        app_commands.Choice(name="Bass boost", value="bassboost"),
        app_commands.Choice(name="Nightcore", value="nightcore"),
        app_commands.Choice(name="Vaporwave", value="vaporwave"),
    ])
    async def filter(self, interaction: discord.Interaction, preset: app_commands.Choice[str]):
        player = self.player(interaction)
        filters = wavelink.Filters()
        if preset.value == "bassboost":
            filters.equalizer.set(
                bands=[
                    {"band": index, "gain": gain}
                    for index, gain in enumerate(
                        [0.30, 0.25, 0.20, 0.12, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                    )
                ]
            )
        elif preset.value == "nightcore":
            filters.timescale.set(speed=1.18, pitch=1.18, rate=1.0)
        elif preset.value == "vaporwave":
            filters.timescale.set(speed=0.82, pitch=0.82, rate=1.0)
        await player.set_filters(filters)
        await interaction.response.send_message(f"Filter set to **{preset.name}**.")

    @music.command(name="status", description="Show Lavalink and player readiness.")
    async def status(self, interaction: discord.Interaction):
        health = self.health()
        player = interaction.guild.voice_client

        def capability(value, ready: str, missing: str) -> str:
            if value is None:
                return "not confirmed"
            return ready if value else missing

        lines = [
            f"- feature: **{'enabled' if health['enabled'] else 'disabled'}**",
            f"- Lavalink: **{'connected' if health['ready'] else 'not connected'}**",
            f"- node: `{settings.lavalink_identifier}` · {health['nodes']} configured",
            f"- active players: **{health['players']}**",
            "- LavaSrc: **"
            + capability(health["lavasrc_loaded"], "loaded", "missing")
            + "**",
            "- Spotify resolution: **"
            + capability(health["spotify_source"], "ready", "unavailable")
            + "**",
            "- modern YouTube plugin: **"
            + capability(health["youtube_plugin"], "loaded", "missing/legacy")
            + "**",
            "- YouTube source: **"
            + capability(health["youtube_source"], "ready", "unavailable")
            + "**",
        ]
        if isinstance(player, wavelink.Player):
            lines.extend(
                [
                    f"- this server: {player.channel.mention}",
                    f"- queue: {player.queue.count} · volume: {player.volume}%",
                ]
            )
        if health["error"]:
            lines.append(f"- issue: {health['error'][:500]}")
        if health["capability_error"]:
            lines.append(f"- capability probe: {health['capability_error'][:500]}")
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Nexy Music Status",
                description="\n".join(lines),
                colour=MUSIC_COLOUR,
            ),
            ephemeral=True,
        )

    @music.command(name="help", description="Show every Nexy music command.")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Nexy Music Commands",
            description=(
                "**Start**\n"
                "`/music join` · `/music play` · `/music playnext`\n\n"
                "**Playback**\n"
                "`pause` · `resume` · `skip` · `previous` · `replay` · `stop`\n\n"
                "**Queue**\n"
                "`queue` · `remove` · `move` · `jump` · `shuffle` · `clear`\n\n"
                "**Sound**\n"
                "`volume` · `seek` · `loop` · `autoplay` · `filter`\n\n"
                "**Session**\n"
                "`nowplaying` · `status` · `disconnect` · `leave`"
            ),
            colour=MUSIC_COLOUR,
        )
        embed.set_footer(text="Queries accept searches, YouTube URLs, Spotify URLs, and playlists.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        track = getattr(payload, "track", None)
        if player is None or player.guild is None or track is None:
            return

        guild_id = player.guild.id
        if player.guild.voice_client is not player or not player.connected:
            logger.info(
                "Ignored stale Lavalink TrackStart guild=%s node=%s track=%s",
                guild_id,
                self._node_identifier(player.node),
                track_identity(track),
            )
            return

        restore_mode = self.loop_modes_to_restore.pop(guild_id, None)
        if restore_mode is not None and player.queue.mode is wavelink.QueueMode.normal:
            player.queue.mode = restore_mode
        audio_coordinator.claim(guild_id, "music")
        self.cancel_pending_announcement(guild_id)
        task = asyncio.create_task(
            self.announce_after_start(player, track),
            name=f"nexy-now-playing-{guild_id}",
        )
        self.announcement_tasks[guild_id] = (track_identity(track), task)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        track = getattr(payload, "track", None)
        if player is None or player.guild is None:
            return
        self.cancel_pending_announcement(
            player.guild.id,
            track_identity(track) if track is not None else None,
        )
        if track is not None:
            advance = self.failure_advance_tasks.get(player.guild.id)
            if advance is not None and advance[0] == track_identity(track):
                self.failure_advance_tasks.pop(player.guild.id, None)
                advance[1].cancel()

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        player = payload.player
        track = getattr(payload, "track", None)
        exception = getattr(payload, "exception", None)
        failure = LavalinkFailure.from_exception(exception)
        node = getattr(player, "node", None)
        node_name = self._node_identifier(node) if node is not None else "unknown"
        guild_id = player.guild.id if player is not None and player.guild is not None else "unknown"
        source = track_source_name(track) if track is not None else "unknown"
        identifier = getattr(track, "identifier", "unknown") if track is not None else "unknown"
        logger.error(
            "Lavalink track exception guild=%s node=%s source=%s identifier=%s "
            "severity=%s message=%s cause=%s",
            guild_id,
            node_name,
            source,
            identifier,
            failure.severity[:100],
            failure.message[:1000],
            failure.cause[:1000],
        )

        if player is None or player.guild is None or track is None:
            return

        guild_id = player.guild.id
        track_key = track_identity(track)
        self.cancel_pending_announcement(guild_id, track_key)

        # Wavelink's loop mode deliberately returns the loaded track again.
        # Temporarily bypass it for a failed source, then restore the user's
        # mode only after a different track actually starts.
        if player.queue.mode is wavelink.QueueMode.loop:
            self.loop_modes_to_restore[guild_id] = wavelink.QueueMode.loop
            player.queue.mode = wavelink.QueueMode.normal
        elif player.queue.mode is wavelink.QueueMode.loop_all:
            history = player.queue.history
            if history is not None:
                for index in range(history.count - 1, -1, -1):
                    if track_identity(history.get_at(index)) == track_key:
                        history.delete(index)
                        break

        fallback = await self.try_spotify_fallback(player, track)
        self.schedule_failed_track_advance(player, track)
        if fallback == "playing":
            message = "⚠️ The Spotify mirror failed; trying a YouTube fallback now."
        elif fallback == "queued":
            message = "⚠️ The Spotify mirror failed; a YouTube fallback is queued next."
        else:
            capabilities = self.capabilities_for(player.node)
            if source.startswith("youtube") and capabilities.probed and not capabilities.youtube_plugin_loaded:
                message = (
                    "⚠️ This YouTube track failed and the Lavalink node does not "
                    "report the modern YouTube plugin. Skipping it."
                )
            else:
                message = "⚠️ This track failed during playback; skipping it."
        await self.send_failure_notice(guild_id, track_key, message)

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        player = payload.player
        track = getattr(payload, "track", None)
        if player is None or player.guild is None or track is None:
            return
        threshold = getattr(payload, "threshold", "unknown")
        logger.error(
            "Lavalink track stuck guild=%s node=%s source=%s identifier=%s threshold_ms=%s",
            player.guild.id,
            self._node_identifier(player.node),
            track_source_name(track),
            getattr(track, "identifier", "unknown"),
            threshold,
        )
        track_key = track_identity(track)
        self.cancel_pending_announcement(player.guild.id, track_key)
        await self.send_failure_notice(
            player.guild.id,
            track_key,
            "⚠️ This track stopped producing audio; skipping it.",
        )
        with contextlib.suppress(Exception):
            await player.skip(force=True)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        node = getattr(payload, "node", None)
        if node is not None:
            self.node_error = None
            await self.refresh_node_capabilities(node)

    @commands.Cog.listener()
    async def on_wavelink_node_disconnected(
        self, payload: wavelink.NodeDisconnectedEventPayload
    ):
        node = getattr(payload, "node", None)
        identifier = self._node_identifier(node) if node is not None else "unknown"
        self.node_error = f"Lavalink node {identifier} disconnected; reconnecting."
        self.node_capabilities[identifier] = NodeCapabilities.unknown(
            identifier, self.node_error
        )
        logger.warning("Lavalink node disconnected node=%s", identifier)

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        guild_id = player.guild.id if player.guild else None
        self.clear_player(player)
        await player.disconnect()
        if guild_id:
            self.release_guild(guild_id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Release Lavalink resources when the last human leaves a channel."""
        if self.bot.user is not None and member.id == self.bot.user.id:
            if before.channel is not None and after.channel is None:
                self.release_guild(member.guild.id)
            return

        if member.bot or before.channel is None or before.channel == after.channel:
            return

        player = member.guild.voice_client
        if not isinstance(player, wavelink.Player) or player.channel != before.channel:
            return

        if any(not occupant.bot for occupant in before.channel.members):
            return

        guild_id = member.guild.id
        self.clear_player(player)
        await player.disconnect()
        self.release_guild(guild_id)


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCommands(bot))
