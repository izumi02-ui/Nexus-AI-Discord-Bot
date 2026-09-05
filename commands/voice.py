"""Turn-based live voice conversations with Project Nexus (Nexy)."""

from __future__ import annotations

import asyncio
import contextlib
import pathlib
import tempfile
import time

import discord
from discord import app_commands
from discord.ext import commands, voice_recv

from ai.engine import engine
from media.audio_coordinator import audio_coordinator
from media.common import speakable_text, truncate
from media.dave_compat import install_voice_receive_dave_patch
from media.speech import (
    GroqSpeech,
    SpeechModelAccessError,
    VOICE_CONTEXT,
    ffmpeg_executable,
)
from media.voice_buffer import (
    DuplicateTranscriptGuard,
    Utterance,
    UtteranceBuffer,
)
from utils.discord_utils import safe_text
from utils.logger import logger
from utils.permissions import is_admin
from utils.settings import settings


VOICE_COLOUR = discord.Colour.from_rgb(46, 204, 113)
DAVE_COMPATIBILITY = install_voice_receive_dave_patch()


class VoiceError(RuntimeError):
    """A voice-chat error that is safe to show to a Discord user."""


class VoiceSession:
    """One guild's receive -> transcribe -> answer -> speak pipeline."""

    def __init__(
        self,
        cog: "VoiceCommands",
        voice_client: voice_recv.VoiceRecvClient,
        text_channel: discord.abc.Messageable,
    ):
        self.cog = cog
        self.bot = cog.bot
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.speech = GroqSpeech()
        self.loop = asyncio.get_running_loop()
        self.buffer = UtteranceBuffer(
            silence_seconds=settings.voice_silence_seconds,
            minimum_seconds=settings.voice_min_utterance_seconds,
            maximum_seconds=settings.voice_max_utterance_seconds,
            minimum_rms=settings.voice_rms_threshold,
            max_ready=8,
            max_speakers=8,
        )
        self.transcript_guard = DuplicateTranscriptGuard(
            window_seconds=settings.voice_duplicate_window_seconds
        )
        self.turns: asyncio.Queue[Utterance] = asyncio.Queue(maxsize=8)
        self.segment_task: asyncio.Task | None = None
        self.worker_task: asyncio.Task | None = None
        self.restart_task: asyncio.Task | None = None
        self.playback_lock = asyncio.Lock()
        self.receiver_restart_used = False
        self.listening = False
        self.muted = False
        self.speaking = False
        self.closed = False
        self.last_error_notice_at = float("-inf")
        self.tts_available: bool | None = None
        self.speech_access_notice_key: tuple[str, str, str] | None = None

    def start(self) -> None:
        self.start_listening()
        self.segment_task = asyncio.create_task(
            self._segment_loop(), name=f"nexy-segments-{self.voice_client.guild.id}"
        )
        self.worker_task = asyncio.create_task(
            self._worker_loop(), name=f"nexy-voice-{self.voice_client.guild.id}"
        )

    def start_listening(self) -> None:
        if self.closed or self.listening:
            return

        self.muted = False
        self.voice_client.listen(
            voice_recv.BasicSink(self._receive_packet, decode=True),
            after=self._listen_finished,
        )
        self.listening = True

    def pause_listening(self) -> None:
        self.muted = True
        if self.listening:
            self.listening = False
            self.voice_client.stop_listening()
        self.buffer.clear()
        self.transcript_guard.clear()
        self._discard_pending_turns()

    def _discard_pending_turns(self) -> None:
        """Drop queued PCM safely after mute or a failed provider turn."""
        while not self.turns.empty():
            with contextlib.suppress(asyncio.QueueEmpty):
                self.turns.get_nowait()
                self.turns.task_done()

    def _listen_finished(self, error: Exception | None) -> None:
        self.listening = False
        if error:
            logger.warning("Voice receiver stopped in guild %s: %s", self.voice_client.guild.id, error)

        if self.closed or self.muted or not self.voice_client.is_connected():
            return

        def schedule_recovery() -> None:
            if self.receiver_restart_used:
                asyncio.create_task(
                    self._close_failed_receiver(),
                    name=f"nexy-listener-close-{self.voice_client.guild.id}",
                )
                return

            if self.restart_task is None or self.restart_task.done():
                self.receiver_restart_used = True
                self.restart_task = asyncio.create_task(
                    self._restart_listener(),
                    name=f"nexy-listener-restart-{self.voice_client.guild.id}",
                )

        self.loop.call_soon_threadsafe(schedule_recovery)

    async def _restart_listener(self) -> None:
        """Recover the receive worker without taking the whole bot offline."""
        await asyncio.sleep(1)
        if self.closed or self.muted or not self.voice_client.is_connected():
            return
        try:
            self.start_listening()
            logger.info("Voice receiver restarted in guild %s.", self.voice_client.guild.id)
        except Exception as error:  # noqa: BLE001
            logger.warning("Voice receiver restart failed in guild %s: %s", self.voice_client.guild.id, error)
            asyncio.create_task(
                self._close_failed_receiver(),
                name=f"nexy-listener-close-{self.voice_client.guild.id}",
            )

    async def _close_failed_receiver(self) -> None:
        guild_id = self.voice_client.guild.id
        if self.closed or self.cog.sessions.get(guild_id) is not self:
            return
        await self._notice(
            "⚠️ Live listening stopped because Discord voice receive could not recover. "
            "Use `/voice start` to open a fresh session."
        )
        await self.cog.stop_guild(guild_id, disconnect=True)

    def _receive_packet(self, user, data: voice_recv.VoiceData) -> None:
        """Runs in the receiver thread; never perform network or AI work here."""
        if (
            self.closed
            or not self.listening
            or self.speaking
            or user is None
            or getattr(user, "bot", False)
        ):
            return

        self.buffer.feed(
            user.id,
            getattr(user, "display_name", getattr(user, "name", str(user.id))),
            data.pcm,
        )

    async def _segment_loop(self) -> None:
        try:
            while not self.closed:
                await asyncio.sleep(0.2)

                if not self.listening or self.speaking:
                    continue

                for turn in self.buffer.drain_ready():
                    if self.turns.full():
                        logger.info("Dropped voice turn in guild %s: queue full", self.voice_client.guild.id)
                        continue
                    self.turns.put_nowait(turn)
        except asyncio.CancelledError:
            pass

    async def _worker_loop(self) -> None:
        try:
            while not self.closed:
                turn = await self.turns.get()
                try:
                    await self._answer_turn(turn)
                except asyncio.CancelledError:
                    raise
                except SpeechModelAccessError as error:
                    logger.warning(
                        "Groq speech access denied in guild %s operation=%s "
                        "model=%s code=%s; listening remains active",
                        self.voice_client.guild.id,
                        error.operation,
                        error.model,
                        error.code,
                    )
                    await self._notice_speech_access_error(error)
                except Exception as error:  # noqa: BLE001 - keep later turns alive
                    logger.exception("Voice turn failed in guild %s", self.voice_client.guild.id)
                    self.buffer.clear()
                    self._discard_pending_turns()
                    await self._notice_turn_error()
                finally:
                    self.turns.task_done()
        except asyncio.CancelledError:
            pass

    async def _answer_turn(self, turn: Utterance) -> None:
        transcript = await self.speech.transcribe(turn.pcm)

        # The raw PCM bytes are no longer referenced after transcription. Tiny
        # or empty transcriptions are usually packet noise, not a user request.
        transcript = " ".join(transcript.split()).strip()
        if len(transcript) < 2:
            return
        if self.transcript_guard.is_duplicate(turn.user_id, transcript):
            logger.info(
                "Ignored duplicate voice transcript in guild %s from user %s",
                self.voice_client.guild.id,
                turn.user_id,
            )
            return

        outcome = await engine.respond(
            user_id=turn.user_id,
            message=transcript,
            context_note=VOICE_CONTEXT,
            include_footer=False,
        )
        written = outcome.get("raw") or outcome.get("response") or ""
        spoken = speakable_text(
            outcome.get("raw") or written,
            limit=settings.voice_max_reply_chars,
        )

        transcript_posted = settings.voice_transcripts
        if transcript_posted:
            await self._post_transcript(turn, transcript, written)

        try:
            audio = await self.speech.synthesize(spoken)
        except SpeechModelAccessError as error:
            if (
                error.operation == "tts"
                and settings.voice_tts_text_fallback
                and not transcript_posted
            ):
                await self._post_transcript(turn, transcript, written)
            raise

        self.tts_available = True
        self.speech_access_notice_key = None
        await self._play(audio)

    async def _post_transcript(
        self, turn: Utterance, transcript: str, response: str
    ) -> None:
        message = (
            f"**{safe_text(turn.display_name)}:** {safe_text(truncate(transcript, 450))}\n"
            f"**{settings.nexus_nickname}:** {safe_text(truncate(response, 1350))}"
        )
        await self.text_channel.send(
            message,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _play(self, wav_bytes: bytes) -> None:
        if self.closed or not self.voice_client.is_connected():
            return

        async with self.playback_lock:
            guild_id = self.voice_client.guild.id
            state = audio_coordinator.state_for(guild_id)
            if state.mode not in {None, "voice"}:
                raise VoiceError("Another Nexus audio mode currently owns this guild.")
            if state.mode is None:
                audio_coordinator.claim(guild_id, "voice")

            path: pathlib.Path | None = None
            finished = asyncio.Event()
            loop = asyncio.get_running_loop()

            try:
                with tempfile.NamedTemporaryFile(prefix="nexy-", suffix=".wav", delete=False) as output:
                    output.write(wav_bytes)
                    path = pathlib.Path(output.name)

                source = discord.FFmpegPCMAudio(
                    str(path),
                    executable=ffmpeg_executable(),
                    before_options="-nostdin",
                    options="-vn -loglevel warning",
                )

                def after(error: Exception | None):
                    if error:
                        logger.warning("Nexy TTS playback error: %s", error)
                    loop.call_soon_threadsafe(finished.set)

                self.speaking = True
                audio_coordinator.set_tts_speaking(guild_id, True)
                self.buffer.clear()

                if self.voice_client.is_playing():
                    self.voice_client.stop_playing()

                self.voice_client.play(source, after=after)
                try:
                    await asyncio.wait_for(finished.wait(), timeout=180)
                except asyncio.TimeoutError as error:
                    if self.voice_client.is_playing():
                        self.voice_client.stop_playing()
                    raise VoiceError("Speech playback timed out.") from error
            finally:
                self.speaking = False
                audio_coordinator.set_tts_speaking(guild_id, False)
                if path is not None:
                    with contextlib.suppress(OSError):
                        path.unlink()

    async def _notice(self, text: str) -> None:
        with contextlib.suppress(discord.HTTPException):
            await self.text_channel.send(
                text,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    async def _notice_turn_error(self) -> None:
        stamp = time.monotonic()
        if stamp - self.last_error_notice_at < settings.voice_error_cooldown_seconds:
            return
        self.last_error_notice_at = stamp
        await self._notice(
            "⚠️ Nexy could not complete that voice turn. The pending audio queue "
            "was cleared; please try speaking again in a moment."
        )

    async def _notice_speech_access_error(
        self, error: SpeechModelAccessError
    ) -> None:
        """Report one access error per model/code while continuing the session."""
        key = (error.operation, error.model, error.code)
        if error.operation == "tts":
            self.tts_available = False
        if self.speech_access_notice_key == key:
            return
        self.speech_access_notice_key = key

        if error.operation == "tts":
            fallback = (
                "Nexy can still listen and reply in text, but "
                if settings.voice_tts_text_fallback
                else "Nexy can still listen, but "
            )
            await self._notice(
                f"⚠️ {fallback}Groq denied TTS access to `{error.model}` "
                f"(`{error.code}`). The Groq organization/project that issued "
                "`GROQ_API_KEY` must have Orpheus access and its model terms "
                "accepted. Listening remains active."
            )
            return

        await self._notice(
            f"⚠️ Groq denied speech-recognition access to `{error.model}` "
            f"(`{error.code}`). Check the organization/project associated with "
            "`GROQ_API_KEY`. The session remains connected and will retry."
        )

    async def stop(self, *, disconnect: bool) -> None:
        if self.closed:
            return

        self.closed = True
        self.pause_listening()

        for task in (self.segment_task, self.worker_task, self.restart_task):
            if task is not None:
                task.cancel()

        tasks = [
            task
            for task in (self.segment_task, self.worker_task, self.restart_task)
            if task is not None
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._discard_pending_turns()

        if self.voice_client.is_playing():
            self.voice_client.stop_playing()

        if disconnect and self.voice_client.is_connected():
            await self.voice_client.disconnect(force=True)


class VoiceCommands(commands.Cog):
    """Commands for private, ephemeral live voice turns with Nexy."""

    voice = app_commands.Group(
        name="voice",
        description="Live voice conversation with Nexy.",
        guild_only=True,
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions: dict[int, VoiceSession] = {}

    def lock_for(self, guild_id: int) -> asyncio.Lock:
        return audio_coordinator.lock_for(guild_id)

    def health(self) -> dict:
        ffmpeg_ready = False
        ffmpeg_error = None
        try:
            ffmpeg_ready = bool(ffmpeg_executable())
        except Exception as error:  # noqa: BLE001
            ffmpeg_error = str(error)
        ready = (
            settings.voice_chat_enabled
            and bool(settings.groq_api_key)
            and ffmpeg_ready
            and DAVE_COMPATIBILITY.ready
        )
        return {
            "enabled": settings.voice_chat_enabled,
            "ready": ready,
            "speech_configured": bool(settings.groq_api_key),
            "ffmpeg_ready": ffmpeg_ready,
            "sessions": len(self.sessions),
            "stt_model": settings.voice_stt_model,
            "tts_provider": settings.voice_tts_provider,
            "tts_model": settings.voice_tts_model,
            "voice": settings.voice_tts_voice,
            "text_fallback": settings.voice_tts_text_fallback,
            "text_mirror": settings.voice_transcripts,
            "noise_gate": settings.voice_rms_threshold,
            "dave_ready": DAVE_COMPATIBILITY.ready,
            "dave_patch": DAVE_COMPATIBILITY.patched,
            "dave_detail": DAVE_COMPATIBILITY.detail,
            "error": ffmpeg_error,
        }

    def ensure_available(self) -> None:
        if not settings.voice_chat_enabled:
            raise VoiceError("Live voice chat is disabled by VOICE_CHAT_ENABLED.")
        if not settings.groq_api_key:
            raise VoiceError("GROQ_API_KEY is required for live speech recognition and voice.")
        if not DAVE_COMPATIBILITY.ready:
            raise VoiceError(DAVE_COMPATIBILITY.detail)
        try:
            ffmpeg_executable()
        except RuntimeError as error:
            raise VoiceError(str(error)) from error

    def user_channel(self, interaction: discord.Interaction):
        state = getattr(interaction.user, "voice", None)
        if state is None or state.channel is None:
            raise VoiceError("Join a voice channel first.")
        return state.channel

    def ensure_same_channel(self, interaction: discord.Interaction, session: VoiceSession):
        channel = self.user_channel(interaction)
        if channel.id != session.voice_client.channel.id and not is_admin(interaction.user):
            raise VoiceError(f"Join {session.voice_client.channel.mention} to control this session.")

    async def start_session(
        self, interaction: discord.Interaction, *, consent: bool
    ) -> VoiceSession:
        if not consent:
            raise VoiceError(
                "Start only after everyone present knows Nexy will transcribe spoken turns "
                "and that the resulting text follows the server's normal Nexus memory settings."
            )

        self.ensure_available()
        channel = self.user_channel(interaction)
        guild = interaction.guild

        async with self.lock_for(guild.id):
            existing = self.sessions.get(guild.id)
            if existing is not None and not existing.closed:
                self.ensure_same_channel(interaction, existing)
                existing.text_channel = interaction.channel
                existing.start_listening()
                audio_coordinator.claim(guild.id, "voice")
                return existing

            voice_client = guild.voice_client
            if voice_client is not None:
                music_cog = self.bot.get_cog("MusicCommands")
                if music_cog is not None and await music_cog.stop_guild(
                    guild.id, disconnect=True
                ):
                    voice_client = None
                if voice_client is not None:
                    await voice_client.disconnect(force=True)

            receiver: voice_recv.VoiceRecvClient = await channel.connect(
                cls=voice_recv.VoiceRecvClient,
                self_deaf=False,
            )
            session = VoiceSession(self, receiver, interaction.channel)
            self.sessions[guild.id] = session
            audio_coordinator.claim(guild.id, "voice")
            session.start()
            return session

    async def stop_guild(self, guild_id: int, *, disconnect: bool) -> bool:
        session = self.sessions.pop(guild_id, None)
        if session is None:
            guild = self.bot.get_guild(guild_id)
            client = guild.voice_client if guild else None
            if disconnect and isinstance(client, voice_recv.VoiceRecvClient):
                await client.disconnect(force=True)
                audio_coordinator.release(guild_id, "voice")
                return True
            audio_coordinator.release(guild_id, "voice")
            return False
        await session.stop(disconnect=disconnect)
        audio_coordinator.release(guild_id, "voice")
        return True

    async def send_error(self, interaction: discord.Interaction, error: Exception):
        content = f"⚠️ {str(error)[:1200]}"
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        original = getattr(error, "original", error)
        if isinstance(original, VoiceError):
            await self.send_error(interaction, original)
            return
        logger.error(
            "Voice command failed: %s",
            original,
            exc_info=(type(original), original, original.__traceback__),
        )
        await self.send_error(interaction, VoiceError("Voice command failed. Check Render logs."))

    async def _start_command(self, interaction: discord.Interaction, consent: bool):
        await interaction.response.defer(thinking=True)
        session = await self.start_session(interaction, consent=consent)
        embed = discord.Embed(
            title=f"{settings.nexus_nickname} is listening",
            description=(
                f"Connected to {session.voice_client.channel.mention}. Speak naturally; "
                "a turn is sent after a short pause.\n\n"
                "Audio is buffered only until transcription and is not saved by Nexus. "
                "Transcribed text follows the normal Nexus memory settings. Use "
                "`/voice mute`, `/forget all`, or `/voice leave` at any time."
            ),
            colour=VOICE_COLOUR,
        )
        embed.set_footer(
            text=f"STT: {settings.voice_stt_model} • Voice: {settings.voice_tts_voice}"
        )
        await interaction.followup.send(embed=embed)

    @voice.command(name="join", description="Join your channel and start live conversation.")
    @app_commands.describe(consent="Confirm everyone present knows Nexy will transcribe spoken turns")
    async def join(self, interaction: discord.Interaction, consent: bool):
        await self._start_command(interaction, consent)

    @voice.command(name="start", description="Start or resume live conversation in your channel.")
    @app_commands.describe(consent="Confirm everyone present knows Nexy will transcribe spoken turns")
    async def start(self, interaction: discord.Interaction, consent: bool):
        await self._start_command(interaction, consent)

    @voice.command(name="mute", description="Stop listening but stay in the voice channel.")
    async def mute(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.guild_id)
        if session is None:
            raise VoiceError("No live voice session is active.")
        self.ensure_same_channel(interaction, session)
        session.pause_listening()
        await interaction.response.send_message("Nexy stopped listening. `/voice unmute` resumes.")

    @voice.command(name="unmute", description="Resume listening in the current live session.")
    async def unmute(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.guild_id)
        if session is None:
            raise VoiceError("No live voice session is active; use `/voice start`.")
        self.ensure_same_channel(interaction, session)
        session.start_listening()
        await interaction.response.send_message("Nexy is listening again.")

    @voice.command(name="say", description="Have Nexy speak a short typed message.")
    async def say(self, interaction: discord.Interaction, text: app_commands.Range[str, 1, 200]):
        session = self.sessions.get(interaction.guild_id)
        if session is None:
            raise VoiceError("Start a live voice session first.")
        self.ensure_same_channel(interaction, session)
        await interaction.response.defer(ephemeral=True)
        spoken = speakable_text(text, limit=200)
        try:
            audio = await session.speech.synthesize(spoken)
        except SpeechModelAccessError as error:
            await session._notice_speech_access_error(error)
            raise VoiceError(
                f"Groq denied TTS access to {error.model} ({error.code}). "
                "Check Orpheus access/terms for the organization or project "
                "associated with GROQ_API_KEY."
            ) from error
        await session._play(audio)
        await interaction.followup.send("Spoken.", ephemeral=True)

    async def _leave_command(self, interaction: discord.Interaction):
        session = self.sessions.get(interaction.guild_id)
        if session is not None:
            self.ensure_same_channel(interaction, session)
        stopped = await self.stop_guild(interaction.guild_id, disconnect=True)
        if not stopped:
            raise VoiceError("No live voice session is active.")
        await interaction.response.send_message("Live voice ended and Nexy disconnected.")

    @voice.command(name="stop", description="End live voice and disconnect.")
    async def stop(self, interaction: discord.Interaction):
        await self._leave_command(interaction)

    @voice.command(name="leave", description="End live voice and disconnect.")
    async def leave(self, interaction: discord.Interaction):
        await self._leave_command(interaction)

    @voice.command(name="status", description="Show live voice readiness and current mode.")
    async def status(self, interaction: discord.Interaction):
        health = self.health()
        session = self.sessions.get(interaction.guild_id)
        lines = [
            f"- feature: **{'enabled' if health['enabled'] else 'disabled'}**",
            f"- speech API: **{'ready' if health['speech_configured'] else 'GROQ_API_KEY missing'}**",
            f"- FFmpeg: **{'ready' if health['ffmpeg_ready'] else 'missing'}**",
            f"- Discord DAVE/E2EE: **{'ready' if health['dave_ready'] else 'not ready'}**",
            f"- female voice: `{health['voice']}` via `{health['tts_provider']}/{health['tts_model']}`",
            f"- recognition: `{health['stt_model']}`",
            f"- silence/noise gate: RMS `{health['noise_gate']}`",
            f"- this server: **{'listening' if session and session.listening else 'inactive'}**",
            f"- text mirror: **{'on' if health['text_mirror'] else 'off'}**",
            f"- TTS text fallback: **{'on' if health['text_fallback'] else 'off'}**",
        ]
        if session and session.tts_available is False:
            lines.append("- TTS runtime: **access denied; text fallback active**")
        if health["error"]:
            lines.append(f"- issue: {health['error'][:300]}")
        if not health["dave_ready"]:
            lines.append(f"- DAVE detail: {health['dave_detail'][:300]}")
        embed = discord.Embed(
            title="Nexy Voice Status",
            description="\n".join(lines),
            colour=VOICE_COLOUR,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Close a live session when Nexus disconnects or the room empties."""
        if before.channel is None or before.channel == after.channel:
            return

        session = self.sessions.get(member.guild.id)
        if session is None or session.voice_client.channel != before.channel:
            return

        if self.bot.user is not None and member.id == self.bot.user.id:
            if after.channel is None:
                await self.stop_guild(member.guild.id, disconnect=False)
            return

        if member.bot or any(not occupant.bot for occupant in before.channel.members):
            return

        await session._notice("Live voice ended because the channel is empty.")
        await self.stop_guild(member.guild.id, disconnect=True)

    async def cog_unload(self):
        for guild_id in list(self.sessions):
            with contextlib.suppress(Exception):
                await self.stop_guild(guild_id, disconnect=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCommands(bot))
