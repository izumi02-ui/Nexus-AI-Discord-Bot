"""
Project Nexus

Chat Commands

The commands people actually use to talk to Nexus:

    /ask       a grounded question (same pipeline as pinging the bot)
    /search    raw evidence, before any model touches it
    /sources   what the last answer was built on
    /verify    check one specific claim against live sources

/search and /sources exist on purpose: an assistant that only shows the
conclusion asks for blind trust. Showing the retrieved evidence lets a user
catch a bad source, which is how Nexus' answers stay honest in a community.
"""

import discord
from discord import app_commands
from discord.ext import commands

from ai.engine import engine
from search.aggregator import aggregator
from search.freshness import  label as freshness_label
from utils.cooldown import cooldown
from utils.discord_utils import send_long_message
from utils.logger import logger
from utils.settings import settings


class ChatCommands(commands.Cog):
    """Conversation and evidence commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==========================================
    # /ask
    # ==========================================

    @commands.cooldown(1, 8, commands.BucketType.user)
    @commands.guild_only()
    @app_commands.command(
        name="ask",
        description="Ask Nexus something, checking live sources when needed.",
    )
    @app_commands.describe(question="What do you want to know?")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer(
            thinking=True,
            ephemeral=getattr(interaction, "guild", None) is None,
        )

        if not cooldown.allow("ask", interaction.user.id):
            await interaction.followup.send(
                cooldown.message("ask", interaction.user.id)
                or "⏳ Slow down a moment.",
                ephemeral=True,
            )

            return

        try:
            outcome = await engine.respond(
                user_id=interaction.user.id,
                message=question,
            )
        except Exception as error:  # noqa: BLE001 - surface it, do not go silent
            logger.exception("/ask failed")

            await interaction.followup.send(
                f"⚠️ I could not answer that: {str(error)[:600]}",
                ephemeral=True,
            )

            return

        report = outcome.get("report")
        verification = outcome.get("verification")

        await send_long_message(interaction.followup, outcome["response"])

        if report is not None and verification is not None:
            await interaction.followup.send(
                self._grounding_line(outcome),
                ephemeral=True,
            )

    # ==========================================
    # /search
    # ==========================================

    @app_commands.command(
        name="search",
        description="Search live sources and show what was found, unsummarised.",
    )
    @app_commands.describe(query="What should Nexus look up?")
    @app_commands.describe(tool="Optional: only use one source (e.g. wikipedia)")
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
        tool: str | None = None,
    ):
        await interaction.response.defer(thinking=True)

        if not cooldown.allow("search", interaction.user.id):
            await interaction.followup.send(
                cooldown.message("search", interaction.user.id),
                ephemeral=True,
            )

            return

        from tools.manager import tool_manager

        tools = None

        if tool:
            available = [name for name in tool_manager.tools]

            if tool not in available:
                await interaction.followup.send(
                    f"❓ Unknown source `{tool}`. Available: "
                    + ", ".join(f"`{name}`" for name in sorted(available)[:12]),
                    ephemeral=True,
                )

                return

            tools = [tool]

        report = await aggregator.search(query, tools)

        if report.is_empty:
            await interaction.followup.send(
                "🔍 Nothing usable came back.\n"
                + (
                    f"- Skipped: {', '.join(report.tools_skipped)}\n"
                    if report.tools_skipped else ""
                )
                + (
                    "- Failed: "
                    + "; ".join(f"{name}: {why[:60]}" for name, why in list(report.tools_failed.items())[:3])
                    if report.tools_failed
                    else ""
                )
            )

            return

        lines = [
            f"## 🔍 Search: {query}",
            f"- {len(report)} result(s) from {len(report.domains)} domain(s)"
            f" · mean confidence {report.mean_confidence}"
            f" · freshness: {freshness_label(query)}",
            f"- tools: {', '.join(report.tools_used) or 'cache'}"
            + (f" · failed: {', '.join(report.tools_failed)}" if report.tools_failed else ""),
        ]

        if report.cross.get("conflicts"):
            conflict = report.cross["conflicts"][0]

            lines.append(
                f"- ⚠️ sources disagree about {conflict['kind']}: "
                + " vs ".join(conflict["values"][:3])
            )

        for index, result in enumerate(report.results[:5], start=1):
            excerpt = (result.content or "").replace("\n", " ")

            lines.append(
                f"\n**{index}. {result.title}** — {result.source}"
                + (f" _(published {result.published_at[:10]})_" if result.published_at else "")
                + f"\n> {excerpt[:420]}"
                + (f"\n<{result.url}>" if result.url else "")
            )

        await send_long_message(interaction.followup, "\n".join(lines))

    # ==========================================
    # /sources
    # ==========================================

    @app_commands.command(
        name="sources",
        description="Show the sources behind Nexus' last answer to you.",
    )
    async def sources(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        entry = engine.last_report(interaction.user.id)

        if not entry:
            await interaction.followup.send(
                "I have not answered anything for you in this session yet."
            )

            return

        report = entry.get("report")
        verification = entry.get("verification")

        if report is None or not getattr(report, "results", None):
            await interaction.followup.send(
                f"⚠️ My last answer to you (`{entry['query'][:80]}`) was **not** built on "
                "live sources.\n"
                + (f"- {verification.summary}" if verification else "")
                + "\nAsk me with /search, or say “search for …”, and I will pull sources.",
                ephemeral=True,
            )

            return

        lines = [f"## 📚 Evidence for “{report.query[:90]}”"]

        for index, result in enumerate(report.results[:6], start=1):
            lines.append(
                f"**{index}. {result.title}**\n"
                f"- {result.source} · trust {result.score_of():.2f}"
                + (f" · published {result.published_at[:10]}" if result.published_at else "")
                + (f"\n<{result.url}>" if result.url else "")
            )

        lines.append(f"\n-# {report.status_line()}")

        await send_long_message(interaction.followup, "\n".join(lines))

    # ==========================================
    # /verify
    # ==========================================

    @app_commands.command(
        name="verify",
        description="Check one claim against live sources instead of trusting memory.",
    )
    @app_commands.describe(claim="The statement to check, e.g. 'Python 3.14 was released in 2025'")
    async def verify(self, interaction: discord.Interaction, claim: str):
        await interaction.response.defer(thinking=True)

        report = await aggregator.search(claim, None, use_cache=False, force=True)

        if report.is_empty:
            await interaction.followup.send(
                "⚠️ I could not find anything to check that against, so I cannot "
                "confirm or deny it. That is different from it being false."
            )

            return

        verdict, colour = self._verdict(report)

        lines = [
            f"## 🔎 {verdict}",
            f"- checked against {len(report)} result(s) from "
            f"{len(report.domains)} independent domain(s)",
            f"- confidence: {report.cross.get('confidence', report.mean_confidence)}"
            f" · freshness: {freshness_label(claim)}",
        ]

        for note in report.cross.get("notes", [])[:3]:
            lines.append(f"- note: {note}")

        for conflict in report.cross.get("conflicts", [])[:2]:
            lines.append(
                f"- ⚠️ disagreement on {conflict['kind']}: "
                + " vs ".join(conflict["values"][:3])
            )

        lines.append("")

        for index, result in enumerate(report.results[:3], start=1):
            lines.append(
                f"**{index}. {result.source}** "
                + (f"_{result.published_at[:10]}_" if result.published_at else "")
                + f"\n> {(result.content or '').replace(chr(10), ' ')[:300]}"
                + (f"\n<{result.url}>" if result.url else "")
            )

        embed = discord.Embed(
            description="\n".join(lines)[:4000],
            colour=colour,
        )

        await interaction.followup.send(embed=embed)

    # ==========================================
    # Helpers
    # ==========================================

    def _verdict(self, report):
        if report.cross.get("corroborated") and not report.cross.get("conflicts"):
            return "✅ Supported by independent sources", discord.Colour.green

        if report.cross.get("conflicts"):
            return "⚠️ Sources disagree", discord.Colour.orange

        if report.cross.get("sources", 0) <= 1:
            return "⚠️ Found, but only in one place", discord.Colour.goldenrod

        return "❓ Not confirmed", discord.Colour.red

    def _grounding_line(self, outcome) -> str:
        report = outcome["report"]
        verification = outcome["verification"]
        route = outcome.get("route") or {}

        parts = [
            f"⚙️ {self.bot.user.name} used **{settings.provider}** ({engine.provider.model})",
            f"· route: `{route.get('type', 'chat')}` ({route.get('reason', '')})",
            f"· {verification.summary}",
        ]

        if report is not None:
            parts.append(f"· {report.status_line()}")

        if report is not None and report.tools_used and "cache" not in report.tools_used:
            parts.append(f"· tools: {', '.join(report.tools_used)}")

        if outcome.get("elapsed"):
            parts.append(f"· {outcome['elapsed']:.1f}s")

        return "-# " + " ".join(parts)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCommands(bot))
