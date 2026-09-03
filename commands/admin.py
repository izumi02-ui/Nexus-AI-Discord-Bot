"""
Project Nexus

Admin Commands

Everything that changes how Nexus behaves, restricted to the creator (and, for
read-only diagnostics, to server admins).

The self-update controls live here deliberately. A bot that refreshes its own
knowledge and repairs its own model ids should still be inspectable and
switchable by a human: /nexus status says what it believes and when it last
checked, /nexus reverify re-grounds the claims it is most likely to be wrong
about, and /nexus accuracy changes how strict it is in one command.
"""

import discord
from discord import app_commands
from discord.ext import commands

from ai import model_catalog
from ai.engine import engine
from ai.provider_manager import provider_manager
from config import CREATOR_ID
from core.updater import updater
from database import knowledge
from search.aggregator import aggregator
from tools.manager import tool_manager
from utils import constants
from utils.cooldown import cooldown
from utils.discord_utils import send_long_message
from utils.logger import logger
from utils.permissions import deny_message, is_admin
from utils.settings import settings


class AdminCommands(commands.Cog):
    """Operational controls for Nexus' accuracy and self-updating."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    nexus = app_commands.Group(
        name="nexus",
        description="Project Nexus administration (accuracy, sources, self-update).",
    )

    # ==========================================
    # /nexus status
    # ==========================================

    @nexus.command(
        name="status",
        description="How Nexus is configured, and how accurate it is feeling.",
    )
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(
            ephemeral=not is_admin(interaction.user)
        )

        health = engine.health()
        state = updater.status()

        lines = [
            "## 🛰 Nexus status",
            f"- provider: **{health.get('provider')}** · model `{health.get('model')}`",
            f"- answers this session: {health.get('requests')}"
            f" · grounded {int(health.get('grounded_rate', 0) * 100)}%"
            f" · searched {int(health.get('search_rate', 0) * 100)}%"
            f" · avg {health.get('avg_seconds')}s",
            f"- search mode: `{settings.search_mode}` · citations: "
            f"`{settings.citation_mode}` · min sources: "
            f"{settings.min_sources_for_grounding}",
            f"- cache: {state['cache'].get('entries')} entries · "
            f"{state['cache'].get('hit_rate')} hit rate",
            f"- knowledge: {state['knowledge'].get('active')} active · "
            f"{state['knowledge'].get('stale')} stale · "
            f"{state['knowledge'].get('disputed')} disputed · "
            f"{state['knowledge'].get('due')} due for re-check",
        ]

        usable = [tool.name for tool in tool_manager.usable_tools()]

        lines.append(
            f"- tools answering: {len(usable)}/{len(tool_manager.tools)} "
            f"({', '.join(sorted(usable)) or 'none'})"
        )

        if state.get("last_cycle_at"):
            lines.append(
                f"- self-update: cycle #{state['cycles']} at {state['last_cycle_at']} "
                f"({state['last_cycle_seconds']}s), next in "
                f"{max(0, settings.self_update_interval - (state.get('last_cycle_seconds') or 0))}s "
                f"intervals of {settings.self_update_interval}s"
            )
        else:
            lines.append(
                f"- self-update: {'enabled' if state['enabled'] else 'disabled'}, "
                f"never run in this session"
            )

        if state.get("last_error"):
            lines.append(f"- ⚠️ last updater error: {state['last_error'][:200]}")

        degraded = [
            f"{name}: {info['health'].get('last_error', '')[:90]}"
            for name, info in (
                (name, tool.info())
                for name, tool in tool_manager.tools.items()
            )
            if info["health"].get("last_error")
        ][:3]

        if degraded:
            lines.append("⚠️ recent tool failures:\n" + "\n".join(f"- {row}" for row in degraded))

        await send_long_message(interaction.followup, "\n".join(lines))

    # ==========================================
    # /nexus reverify
    # ==========================================

    @nexus.command(
        name="reverify",
        description="Re-check stored knowledge against live sources right now.",
    )
    @app_commands.describe(
        topic="Optional topic to re-check; leave empty for everything due"
    )
    async def reverify(self, interaction: discord.Interaction, topic: str | None = None):
        if interaction.user.id != CREATOR_ID and not is_admin(interaction.user):
            await interaction.response.send_message(
                deny_message("bot owner or server admins"), ephemeral=True
            )

            return

        if not cooldown.allow("refresh", interaction.user.id):
            await interaction.response.send_message(
                cooldown.message("refresh", interaction.user.id), ephemeral=True
            )

            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        if topic:
            row = knowledge.find(topic)

            if not row:
                await interaction.followup.send(
                    f"🤔 I have nothing stored about “{topic[:60]}”."
                )

                return

            knowledge.mark_stale(row["id"], "manual re-check requested")

        result = await updater.run_once(reason=f"manual by {interaction.user.id}")

        reverified = result.get("reverified", {})

        await interaction.followup.send(
            "## 🔁 Re-verification finished\n"
            f"- checked {reverified.get('checked', 0)} claim(s): "
            f"{reverified.get('confirmed', 0)} confirmed, "
            f"{reverified.get('updated', 0)} corrected, "
            f"{reverified.get('disputed', 0)} disputed, "
            f"{reverified.get('unreachable', 0)} unreachable\n"
            f"- watchlist: {result.get('watched', {}).get('refreshed', 0)} topic(s) refreshed\n"
            f"- maintenance: {result.get('maintenance', {})}\n"
            + (f"- ⚠️ {result['error'][:300]}" if result.get("error") else "")
        )

    # ==========================================
    # /nexus sources (per-tool health)
    # ==========================================

    @nexus.command(
        name="tools",
        description="Which evidence tools are configured, healthy and in cooldown.",
    )
    async def tools(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        rows = [
            "## 🧰 Evidence tools",
            "| tool | ready | tier | last ok | issues |",
            "|---|---|---|---|---|",
        ]

        health = {row["tool"]: row for row in updater.health_rows()}

        for name, tool in sorted(tool_manager.tools.items()):
            info = tool.info()
            health = info["health"]

            state = "✅" if tool.usable else "⛔"

            if tool.implemented and not tool.available:
                state = "🔑"

            record = health.get(name, {})

            rows.append(
                f"| {name} | {state} | {getattr(tool, 'priority', '-')} "
                f"| {health.get('successes', 0)}✓/{health.get('failures', 0)}✗ "
                f"| {(record.get('last_error') or health.get('last_error') or 'ok')[:60]} "
                f"{'· degraded ' + str(health.get('last_success') or '')[:5] if health.get('degraded') else ''} |"
            )

        await send_long_message(interaction.followup, "\n".join(rows))

    # ==========================================
    # /nexus models
    # ==========================================

    @nexus.command(
        name="models",
        description="Re-read provider model lists and repair retired model ids.",
    )
    async def models(self, interaction: discord.Interaction):
        if interaction.user.id != CREATOR_ID:
            await interaction.response.send_message(
                deny_message(), ephemeral=True
            )

            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        summary = await model_catalog.refresh()

        lines = ["## 📇 Model catalog"]

        for key, stats in summary.get("catalog", {}).items():
            lines.append(
                f"- **{key}**: {stats['count']} model(s), {stats['free']} free, "
                f"largest context {stats['largest_context']:,}"
            )

        for change in summary.get("changed", []):
            lines.append(
                f"- 🔧 {change['provider']}: {', '.join(change['missing'])} no longer "
                f"exists"
                + (
                    f" → now {', '.join(change['chain'])}"
                    if change.get("chain")
                    else " and no replacement was found"
                )
            )

        if summary.get("unavailable"):
            lines.append(
                f"- ⚠️ could not reach: {', '.join(summary['unavailable'])} "
                "(nothing was changed)"
            )

        await send_long_message(interaction.followup, "\n".join(lines))

    # ==========================================
    # /nexus accuracy
    # ==========================================

    @nexus.command(
        name="accuracy",
        description="Tune how hard Nexus verifies before it answers.",
    )
    @app_commands.choices(
        preset=[
            app_commands.Choice(name=name, value=name)
            for name in constants.ACCURACY_PRESETS
        ]
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name=name, value=name)
            for name in constants.SEARCH_MODES
        ]
    )
    @app_commands.describe(
        min_sources="How many independent domains a fact needs (0-4)"
    )
    @app_commands.describe(citations="How sources are shown with answers")
    @app_commands.choices(
        citations=[
            app_commands.Choice(name=name, value=name)
            for name in constants.CITATION_MODES
        ]
    )
    async def accuracy(
        self,
        interaction: discord.Interaction,
        preset: app_commands.Choice[str] | None = None,
        mode: app_commands.Choice[str] | None = None,
        min_sources: app_commands.Range[int, 0, 4] | None = None,
        citations: app_commands.Choice[str] | None = None,
    ):
        if interaction.user.id != CREATOR_ID:
            await interaction.response.send_message(
                deny_message(), ephemeral=True
            )

            return

        values = dict(constants.ACCURACY_PRESETS[preset.value]) if preset else {}

        if mode:
            values["search_mode"] = mode.value

        if citations:
            values["citation_mode"] = citations.value

        if min_sources is not None:
            values["min_sources_for_grounding"] = int(min_sources)

        if not values:
            await interaction.response.send_message(
                f"- search mode: `{settings.search_mode}`\n"
                f"- verification: `{settings.verification_enabled}`\n"
                f"- auto retry: `{settings.auto_retry_with_search}`\n"
                f"- min sources: `{settings.min_sources_for_grounding}`\n"
                f"- citations: `{settings.citation_mode}`\n"
                "-# Changes apply to this session only; config.py stays authoritative.",
                ephemeral=True,
            )

            return

        changed = settings.update(**values)

        await interaction.response.send_message(
            "🎯 Accuracy policy updated (this session):\n"
            + "\n".join(
                f"- `{key}`: `{before}` → `{after}`"
                for key, (before, after) in changed.items()
            )
        )

        logger.info(
            "Accuracy settings changed by %s: %s",
            interaction.user.id,
            values,
        )

    # ==========================================
    # /nexus knowledge
    # ==========================================

    @nexus.command(
        name="knowledge",
        description="Inspect the verified-knowledge store.",
    )
    @app_commands.describe(search="Text to look for")
    async def knowledge_command(
        self,
        interaction: discord.Interaction,
        search: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        rows = (
            knowledge.recall(search, limit=8)
            if search
            else knowledge.recent_changes(limit=8)
        )

        stats = knowledge.stats()

        if not rows:
            await interaction.followup.send(
                "📚 The knowledge store has nothing matching that. "
                f"({stats.get('active')} active entries.)"
            )

            return

        lines = [
            f"## 📚 Verified knowledge ({stats.get('active')} active, "
            f"mean confidence {stats.get('mean_confidence')})"
        ]

        for row in rows:
            flag = {
                "active": "🟢",
                "stale": "🟡",
                "disputed": "🔴",
            }.get(row.get("status", "active"), "⚪")

            lines.append(
                f"{flag} **{row.get('topic', '?')}** — {str(row.get('value'))[:220]}\n"
                f"-# confidence {float(row.get('confidence') or 0):.2f}"
                + (f" · hits {row['hits']}" if row.get("hits") else "")
                + (f" · {row.get('source')}" if row.get("source") else "")
                + (f" · {str(row.get('updated_at'))[:16]}" if row.get("updated_at") else "")
            )

        await send_long_message(interaction.followup, "\n".join(lines))

    # ==========================================
    # /nexus provider
    # ==========================================

    @nexus.command(
        name="provider",
        description="Switch which provider answers (or reset failure counters).",
    )
    @app_commands.describe(name="Provider key, e.g. openrouter, groq, ollama")
    async def provider(self, interaction: discord.Interaction, name: str | None = None):
        if interaction.user.id != CREATOR_ID:
            await interaction.response.send_message(
                deny_message(), ephemeral=True
            )

            return

        if not name:
            status = provider_manager.status()

            lines = ["## 🔌 Providers", f"- active: **{status['active']}**", ""]

            for key, info in status["providers"].items():
                breaker = status["breakers"].get(key, {})

                lines.append(
                    f"- `{key}` — {'✅' if info['available'] else '⛔'} "
                    f"model `{info['model']}`"
                    + (
                        f" · failures {breaker.get('failures', 0)}"
                        + (f" · cooling {breaker.get('cooling_for')}s" if breaker.get("cooling") else "")
                        if breaker
                        else ""
                    )
                )

            await interaction.response.send_message("\n".join(lines), ephemeral=True)

            return

        if name.lower() in {"reset", "clear"}:
            provider_manager.reset_breakers()

            await interaction.response.send_message(
                "🔄 Provider failure counters reset.", ephemeral=True
            )

            return

        provider = provider_manager.set_provider(name)

        if provider is None:
            await interaction.response.send_message(
                f"⛔ `{name}` is not available here.", ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"🔌 Now answering from **{provider.name}** (`{provider.model}`)."
        )

    @nexus.command(
        name="start-updating",
        description="Start or stop the background knowledge updater.",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="start", value="start"),
            app_commands.Choice(name="stop", value="stop"),
            app_commands.Choice(name="run once", value="once"),
        ]
    )
    async def start_updating(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
    ):
        if interaction.user.id != CREATOR_ID:
            await interaction.response.send_message(
                deny_message(), ephemeral=True
            )

            return

        if action.value == "start":
            updater.start()

            await interaction.response.send_message(
                f"▶️ Self-update loop running every "
                f"{settings.self_update_interval}s."
            )

            return

        if action.value == "stop":
            await updater.stop()

            await interaction.response.send_message(
                "⏸️ Self-update loop stopped. Nexus will still learn from "
                "answers it verifies; it just will not go looking on its own."
            )

            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        result = await updater.run_once(reason="manual")

        await interaction.followup.send(
            f"✅ Cycle finished in {result['seconds']}s · "
            f"{result.get('runtime', {}).get('written', 0)} runtime fact(s), "
            f"{result.get('reverified', {}).get('checked', 0)} rechecked, "
            f"{result.get('watched', {}).get('refreshed', 0)} watched topics, "
            f"tools healthy {result.get('tools', {}).get('healthy', '-')}/"
            f"{result.get('tools', {}).get('checked', '-')}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommands(bot))
