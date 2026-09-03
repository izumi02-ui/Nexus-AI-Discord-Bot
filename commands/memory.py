"""
Project Nexus

Memory Commands

Explicit control over what Nexus remembers about you.

Memory is opt-out-able by design: a user who can see the exact rows behind the
bot's personalisation can delete the one that is wrong, which is the difference
between "helpful memory" and "creepy model". Every command here is ephemeral
so nobody else in the channel sees what was remembered or forgotten.
"""

import discord
from discord import app_commands
from discord.ext import commands

from database import fact_manager
from utils.discord_utils import send_long_message
from utils.logger import logger


class MemoryCommands(commands.Cog):
    """Personal memory commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="remember",
        description="Tell Nexus something to keep in mind.",
    )
    @app_commands.describe(fact="e.g. 'my GPU is an RTX 3070'")
    @app_commands.describe(
        category="Optional label such as hardware, project or food"
    )
    async def remember(
        self,
        interaction: discord.Interaction,
        fact: str,
        category: str | None = None,
    ):
        result = fact_manager.remember_fact(
            interaction.user.id,
            fact,
            category=category or "user",
            source="command",
        )

        action = result.get("action", "added")

        if action == "rejected":
            await interaction.response.send_message(
                f"⚠️ I did not store that ({result.get('reason', 'invalid')}).",
                ephemeral=True,
            )

            return

        messages = {
            "added": "🧠 Got it - I will remember that about you.",
            "replaced": "🧠 Updated what I had: the older note about that is now "
                        "superseded by this one.",
            "unchanged": "🧠 I already had that noted.",
        }

        await interaction.response.send_message(
            messages.get(action, "🧠 Saved.")
            + f"\n-# {result.get('fact', fact)[:600]}",
            ephemeral=True,
        )

    @app_commands.command(
        name="forget",
        description="Delete something Nexus remembers about you.",
    )
    @app_commands.describe(term="A word from the note, or 'all' to wipe memory")
    async def forget(self, interaction: discord.Interaction, term: str):
        user_id = interaction.user.id

        if term.strip().lower() in {"all", "everything", "*"}:
            fact_manager.clear_facts(user_id)

            await interaction.response.send_message(
                "🗑️ Cleared everything I remembered about you.",
                ephemeral=True,
            )

            return

        matches = fact_manager.find(user_id, term)

        if not matches:
            await interaction.response.send_message(
                f"🤔 I do not have anything about “{term[:80]}”.",
                ephemeral=True,
            )

            return

        for row in matches:
            fact_manager.delete_fact(user_id, row["fact"])

        await interaction.response.send_message(
            "🗑️ Forgot "
            + "; ".join(f"~~{row['fact'][:90]}~~" for row in matches[:4])
            + (f" (+{len(matches) - 4} more)" if len(matches) > 4 else ""),
            ephemeral=True,
        )

    @app_commands.command(
        name="facts",
        description="Show what Nexus currently remembers about you.",
    )
    async def facts(self, interaction: discord.Interaction):
        rows = fact_manager.fact_rows(interaction.user.id, limit=40)

        stats = fact_manager.stats(interaction.user.id)

        if not rows:
            await interaction.response.send_message(
                "🧠 I have nothing stored about you yet. Use /remember if you "
                "want me to keep something in mind.",
                ephemeral=True,
            )

            return

        lines = [f"## 🧠 What I remember ({stats.get('active', len(rows))} fact(s))"]

        for row in rows:
            marker = ""

            if row["superseded_by"]:
                marker = " ~~(superseded)~~"
            elif row.get("confidence") is not None and float(row["confidence"]) < 0.6:
                marker = " _(low confidence)_"

            lines.append(
                f"- {row['fact'][:400]}{marker}\n"
                f"-# `{row.get('category') or 'note'}` · from {row.get('source') or 'conversation'}"
                + (f" · {row['updated_at'][:10]}" if row.get("updated_at") else "")
            )

        await interaction.response.send_message(ephemeral=True, content="")

        await send_long_message(interaction.followup, "\n".join(lines))

        logger.debug(
            "User %s listed %s fact(s).",
            interaction.user.id,
            len(rows),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryCommands(bot))
