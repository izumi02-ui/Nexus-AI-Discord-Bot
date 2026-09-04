"""
Project Nexus

Discord Bot Entry Point

Wiring only. Every behaviour that matters lives behind this file:

    commands/   what users can type
    ai/         routing, retrieval, generation, verification
    core/       the self-updating loop
    database/   memory and the verified-knowledge store

The one thing this file insists on: the bot must come up even when a provider,
an API key or a tool is missing. A chatbot that refuses to start is useless, so
every subsystem here is optional and reports its own state instead.
"""

import asyncio
import importlib
import math
import os
import pkgutil
import traceback

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands

from config import (
    COMMAND_GUILD_ID,
    CREATOR_ID,
    DISCORD_TOKEN,
    VERSION,
)

from ai.engine import engine
from ai.provider_manager import provider_manager

from core.updater import updater

from database.database import setup_database
from database.fact_manager import get_facts

from tools.manager import tool_manager

from utils.cooldown import cooldown
from utils.discord_utils import send_long_message
from utils.logger import logger
from utils.permissions import is_admin
from utils.rich_response import send_ai_response
from utils.settings import settings

COG_PACKAGE = "commands"

#: Files in commands/ that are not cogs.
COG_SKIP = {"__init__"}


# ============================================
# Discord Intents
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True


# ============================================
# Bot
# ============================================

class NexusBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            help_command=commands.MinimalHelpCommand(),
            case_insensitive=True,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/ask  •  mention me",
            ),
        )

        self.started_at = None

    async def setup_hook(self):
        """Load every cog, then publish the slash-command tree."""
        loaded, failed = await load_cogs(self)

        logger.info(
            "Loaded %s cog(s)%s.",
            loaded,
            f" ({', '.join(failed)} failed)" if failed else "",
        )

        try:
            if COMMAND_GUILD_ID:
                guild = discord.Object(id=int(COMMAND_GUILD_ID))

                self.tree.copy_global_to(guild=guild)

                await self.tree.sync(guild=guild)

                logger.info("Slash commands synced to guild %s.", COMMAND_GUILD_ID)
            else:
                await self.tree.sync()

                logger.info("Slash commands synced globally (may take up to an hour).")
        except Exception as error:  # noqa: BLE001 - commands are not fatal
            logger.warning("Slash command sync failed: %s", error)

    async def on_ready(self):
        self.started_at = discord.utils.utcnow()

        logger.info(
            "Project Nexus %s online as %s (%s) in %s guild(s).",
            VERSION,
            self.user,
            self.user.id,
            len(self.guilds),
        )

        print("=" * 40)
        print(f"Logged in as: {self.user}")
        print(f"Bot ID: {self.user.id}")
        print(f"Version: {VERSION}")
        print(
            "Provider: "
            f"{provider_manager.name} ({provider_manager.model})"
        )
        print(f"Tools: {len(tool_manager.usable_tools())} usable")
        print("=" * 40)

        try:
            updater.start()
        except Exception as error:  # noqa: BLE001 - chat must work without it
            logger.warning("Self-update loop did not start: %s", error)

    async def close(self):
        await updater.stop()

        await super().close()


bot = NexusBot()


# ============================================
# Cog loading
# ============================================

async def load_cogs(target: commands.Bot) -> tuple[int, list[str]]:
    package = importlib.import_module(COG_PACKAGE)

    loaded = 0

    failed = []

    for _finder, name, _ispkg in pkgutil.iter_modules(package.__path__):
        if name in COG_SKIP or name.startswith("_"):
            continue

        try:
            await target.load_extension(f"{COG_PACKAGE}.{name}")

            loaded += 1
        except Exception as error:  # noqa: BLE001 - one bad cog must not stop boot
            failed.append(name)

            logger.error(
                "Cog %s failed to load: %s\n%s",
                name,
                error,
                traceback.format_exc(limit=4),
            )

    return loaded, failed


# ============================================
# Render health server
# ============================================

def latency_ms(value) -> int | None:
    """Return a JSON-safe Discord latency during startup and reconnects."""
    try:
        milliseconds = float(value) * 1000
    except (TypeError, ValueError):
        return None

    if not math.isfinite(milliseconds):
        return None

    return round(milliseconds)


async def health_check(request):
    health = engine.health()

    return web.json_response(
        {
            "status": "online",
            "service": "Project Nexus",
            "version": VERSION,
            "provider": health.get("provider"),
            "model": health.get("model"),
            "requests": health.get("requests"),
            "grounded_rate": health.get("grounded_rate"),
            "search_rate": health.get("search_rate"),
            "tools": len(tool_manager.usable_tools()),
            "self_update": {
                "cycles": updater.state["cycles"],
                "last_cycle_at": updater.state["last_cycle_at"],
                "enabled": bool(getattr(settings, "self_update_enabled", True)),
                "interval_seconds": int(settings.self_update_interval),
            },
            "latency_ms": latency_ms(bot.latency),
        }
    )


async def start_health_server():
    app = web.Application()

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(os.getenv("PORT", "10000"))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port,
    )

    await site.start()

    logger.info(
        "Health server listening on port %s.",
        port,
    )

    return runner


# ============================================
# Messages
# ============================================

def attachments_of(message: discord.Message) -> list[str]:
    """
    URLs for anything the user attached.

    Images go to the model as context it may not be able to view (the engine
    says so explicitly); pages and files are worth scraping, so they are
    included either way.
    """
    return [attachment.url for attachment in message.attachments[:3]]


async def answer_for(message: discord.Message, text: str) -> dict:
    return await engine.respond(
        user_id=message.author.id,
        message=text,
        attachments=attachments_of(message),
        include_footer=True,
    )

@bot.event
async def on_message(message: discord.Message):
    # Ignore bots
    if message.author.bot:
        return

    # Respond when mentioned
    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        user_message = (
            message.content
            .replace(f"<@{bot.user.id}>", "")
            .replace(f"<@!{bot.user.id}>", "")
            .strip()
        )

        if not user_message:
            if not message.attachments:
                await message.reply(
                    "Hi! 👋 Ask me anything — I check live sources when the answer "
                    "could be out of date.\n-# `/ask <question>` · `/search <query>` · "
                    "`/sources` shows what I read"
                )

                return

            user_message = "What is in this file?"

        if not cooldown.allow("ask", message.author.id):
            await message.reply(
                cooldown.message("ask", message.author.id),
                mention_author=False,
            )

            return

        try:
            async with message.channel.typing():
                outcome = await answer_for(message, user_message)

            await send_ai_response(
                message.channel,
                outcome,
                message.author,
            )

        except Exception as error:
            logger.exception("Failed to process mention")

            await message.reply(
                f"⚠️ {error}",
                mention_author=False,
            )

    await bot.process_commands(message)


# ============================================
# Prefix commands (kept for text channels without slash access)
# ============================================

@bot.command(
    name="ai",
    help="Talk with Nexus AI.",
)
async def ai(ctx, *, message):
    if not cooldown.allow("ask", ctx.author.id):
        await ctx.send(
            cooldown.message("ask", ctx.author.id)
        )

        return

    async with ctx.typing():
        try:
            outcome = await answer_for(ctx.message, message)

            await send_ai_response(
                ctx,
                outcome,
                ctx.author,
            )

        except Exception as error:
            logger.exception(
                "AI command failed"
            )

            await ctx.send(
                f"⚠️ {error}"
            )


@bot.command(
    name="memory",
    help="Show remembered facts.",
)
async def memory(ctx):
    facts = get_facts(ctx.author.id)

    if not facts:
        await ctx.send(
            "🧠 I don't remember anything about you yet."
        )

        return

    text = "\n".join(
        f"• {fact}"
        for fact in facts
    )

    await send_long_message(
        ctx,
        f"## 🧠 Things I remember about you:\n{text}",
    )


@bot.command(
    name="status",
    help="How Nexus is configured right now (admin).",
)
@commands.check(lambda ctx: is_admin(ctx.author) or ctx.author.id == CREATOR_ID)
async def status(ctx):
    health = engine.health()

    await ctx.send(
        f"**Nexus {VERSION}** · provider `{health.get('provider')}` "
        f"({health.get('model')}) · {len(tool_manager.usable_tools())} tool(s) "
        f"· search mode `{settings.search_mode}`\n"
        f"-# {health.get('requests')} answered, "
        f"{int(health.get('grounded_rate', 0) * 100)}% grounded, "
        f"avg {health.get('avg_seconds')}s · updater cycle "
        f"#{updater.state['cycles']}"
    )


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"⏳ Slow down a moment - try again in {error.retry_after:.0f}s."
        )

        return

    if isinstance(error, (commands.MissingRequiredArgument, app_commands.MissingArguments)):
        await ctx.send(
            "🤔 I need a bit more than that. Try "
            "`!ai <your question>` or `/ask`."
        )

        return

    if isinstance(error, commands.CheckFailure):
        await ctx.send("⛔ You do not have access to that command.")

        return

    logger.error(
        "Unhandled command error: %s\n%s",
        error,
        "".join(
            traceback.format_exception(
                type(error),
                error,
                error.__traceback__,
            )
        )[:1200],
    )

    await ctx.send(f"⚠️ {str(error)[:800]}")


# ============================================
# Start Nexus
# ============================================

async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing."
        )

    setup_database()

    runner = await start_health_server()

    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Project Nexus stopped by signal.")
