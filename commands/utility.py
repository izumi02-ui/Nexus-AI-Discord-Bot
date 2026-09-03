"""
Project Nexus

Utility Commands

Small, honest answers about the bot itself. These exist because an accuracy-focused
assistant should not be vague about its own limits: /version reports the running
build, /ping reports real latency, and /tools lists which evidence sources are
actually configured on this instance right now instead of the ones that exist in
the repository.
"""

import time

import discord
from discord import app_commands
from discord.ext import commands

from config import  VERSION
from tools.manager import tool_manager
from utils.discord_utils import send_long_message
from utils.settings import settings


class UtilityCommands(commands.Cog):
    """Self-reporting commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="version",
        description="Which build of Nexus this is, and what it is running on.",
    )
    async def version(self, interaction: discord.Interaction):
        from ai.provider_manager import provider_manager
        from core.updater import updater

        state = updater.status()

        await interaction.response.send_message(
            f"**Project Nexus {VERSION}**\n"
            f"- answering from **{provider_manager.name}** "
            f"(`{provider_manager.model}`)\n"
            f"- {len(tool_manager.usable_tools())} evidence tool(s) ready · "
            f"search mode `{settings.search_mode}`\n"
            f"- self-update: "
            + (
                f"cycle #{state['cycles']}, last {state['last_cycle_at']}"
                if state.get("last_cycle_at")
                else ("armed, not run yet" if state["enabled"] else "disabled")
            )
            + f"\n-# uptime {self._uptime()} · latency "
            f"{round(self.bot.latency * 1000)} ms · Python "
            f"{discord.__version__} gateway",
            ephemeral=True,
        )

    @app_commands.command(
        name="ping",
        description="Gateway latency and how loaded Nexus is.",
    )
    async def ping(self, interaction: discord.Interaction):
        started = time.perf_counter()

        await interaction.response.defer(ephemeral=True)

        roundtrip = (time.perf_counter() - started) * 1000

        from ai.engine import engine

        stats = engine.stats

        await interaction.followup.send(
            f"🏓 Pong — gateway {round(self.bot.latency * 1000)} ms · "
            f"REST {round(roundtrip)} ms\n"
            f"-# {stats['requests']} answered this session · "
            f"{stats['searches']} with live sources · "
            f"avg {stats['total_seconds'] / max(1, stats['requests']):.1f}s"
        )

    @app_commands.command(
        name="tools",
        description="List the evidence sources this Nexus can consult.",
    )
    async def tools(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        lines = ["## 🧰 Sources Nexus can consult"]

        for name, tool in sorted(tool_manager.tools.items()):
            if not tool.implemented:
                continue

            if tool.usable:
                mark = "✅"
            elif tool.available:
                mark = "⚠️"
            else:
                mark = "🔑"

            lines.append(
                f"{mark} **{name}** — {tool.description[:90]}"
                + (
                    f"\n-# needs {', '.join(tool.required_keys)}"
                    if not tool.available and tool.required_keys
                    else ""
                )
            )

        lines.append(
            "\n-# 🔑 = no API key configured · ⚠️ = configured but failing its "
            "health check. Nexus skips both and says so rather than guessing."
        )

        await send_long_message(interaction.followup, "\n".join(lines))

    def _uptime(self) -> str:
        started = getattr(self.bot, "started_at", None)

        if not started:
            return "unknown"

        delta = discord.utils.utcnow() - started

        hours, remainder = divmod(int(delta.total_seconds()), 3600)

        minutes, seconds = divmod(remainder, 60)

        return (
            f"{hours}h {minutes}m"
            if hours
            else f"{minutes}m {seconds}s"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCommands(bot))
