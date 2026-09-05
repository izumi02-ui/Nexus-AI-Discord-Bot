"""Production Lavalink music controls for Project Nexus (Nexy)."""

from __future__ import annotations

import asyncio
from collections import defaultdict

import discord
import wavelink
from discord import app_commands
from discord.ext import commands

from media.common import format_duration, markdown_link, truncate
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
            self.node_error = None
            logger.info("Lavalink node %s connected.", settings.lavalink_identifier)
        except Exception as error:  # noqa: BLE001 - chat must still start
            self.node_error = str(error)
            logger.warning("Lavalink unavailable: %s", error)

    async def cog_unload(self):
        try:
            await wavelink.Pool.close()
        except Exception:  # noqa: BLE001
            pass

    def health(self) -> dict:
        nodes = list(wavelink.Pool.nodes.values())
        ready = any(node.status is wavelink.NodeStatus.CONNECTED for node in nodes)
        return {
            "enabled": settings.music_enabled,
            "configured": bool(settings.lavalink_uri and settings.lavalink_password),
            "ready": ready,
            "nodes": len(nodes),
            "players": sum(len(node.players) for node in nodes),
            "error": self.node_error,
        }

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
        existing = guild.voice_client

        if isinstance(existing, wavelink.Player) and existing.connected:
            self.ensure_same_channel(interaction, existing)
            return existing

        if existing is not None:
            # Live conversation and music use different voice protocols. Stop
            # the old mode cleanly before opening the Lavalink connection.
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
        return player

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

    def add_requester(self, tracks: list[wavelink.Playable], user) -> None:
        for track in tracks:
            track.extras = {
                "requester_id": user.id,
                "requester_name": user.display_name,
            }

    def now_playing_embed(self, player: wavelink.Player) -> discord.Embed:
        track = player.current
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

    async def announce_now_playing(self, player: wavelink.Player) -> None:
        if not settings.music_announce_tracks or player.guild is None:
            return

        channel_id = self.announce_channels.get(player.guild.id)
        channel = self.bot.get_channel(channel_id) if channel_id else None

        if channel is None:
            return

        try:
            await channel.send(
                embed=self.now_playing_embed(player),
                view=MusicControls(self, player.guild.id),
            )
        except discord.HTTPException as error:
            logger.warning("Could not announce track in guild %s: %s", player.guild.id, error)

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
            try:
                found = await wavelink.Playable.search(query.strip())
            except Exception as error:  # noqa: BLE001
                raise MusicError(
                    "I could not load that track. For Spotify links, the Lavalink "
                    "node must have LavaSrc configured."
                ) from error

            if not found:
                raise MusicError("No playable tracks matched that search.")

            is_playlist = isinstance(found, wavelink.Playlist)
            tracks = list(found) if is_playlist else [found[0]]
            capacity = settings.music_max_queue - player.queue.count

            if player.current is None:
                capacity += 1

            if capacity <= 0:
                raise MusicError(f"The queue limit is {settings.music_max_queue} tracks.")

            tracks = tracks[:capacity]
            self.add_requester(tracks, interaction.user)
            self.announce_channels[interaction.guild_id] = interaction.channel_id

            started = None
            if player.current is None:
                started = tracks.pop(0)
                await player.play(
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
                    f"Playing {markdown_link(chosen.title, chosen.uri)}."
                    if started
                    else f"Queued {markdown_link(chosen.title, chosen.uri)}"
                    + (" next." if next_up else f" at position **{player.queue.count}**.")
                )

        await interaction.followup.send(detail)

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
        await player.play(target, add_history=True)
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
        await player.play(target)
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
        lines = [
            f"- feature: **{'enabled' if health['enabled'] else 'disabled'}**",
            f"- Lavalink: **{'connected' if health['ready'] else 'not connected'}**",
            f"- node: `{settings.lavalink_identifier}` · {health['nodes']} configured",
            f"- active players: **{health['players']}**",
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
        if payload.player is not None:
            await self.announce_now_playing(payload.player)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        player = payload.player
        if player is None or player.guild is None:
            return
        logger.warning("Track failed in guild %s: %s", player.guild.id, payload.exception)
        channel_id = self.announce_channels.get(player.guild.id)
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if channel:
            await channel.send("⚠️ That track failed on Lavalink; moving to the next item.")

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
