"""
Project Nexus

Discord Bot Entry Point
"""

import asyncio
import os

import discord
from aiohttp import web
from discord.ext import commands

from config import DISCORD_TOKEN

from ai.engine import engine

from database.database import setup_database
from database.fact_manager import get_facts

from utils.logger import logger
from utils.discord_utils import send_long_message


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

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
)


# ============================================
# Render Health Server
# ============================================

async def health_check(request):
    return web.json_response({
        "status": "online",
        "service": "Project Nexus",
    })


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
# Events
# ============================================

@bot.event
async def on_ready():
    setup_database()

    print("=" * 40)
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("=" * 40)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="the Nexus",
        )
    )

    logger.info("Project Nexus is online.")


@bot.event
async def on_message(message):
    # Ignore bots
    if message.author.bot:
        return

    # Respond when mentioned
    if bot.user in message.mentions:
        async with message.channel.typing():
            user_message = (
                message.content
                .replace(f"<@{bot.user.id}>", "")
                .replace(f"<@!{bot.user.id}>", "")
                .strip()
            )

            if not user_message:
                await message.reply(
                    "Hi! 👋 What can I help you with?"
                )
                return

            try:
                response = await engine.ask(
                    user_id=message.author.id,
                    message=user_message,
                )

                await send_long_message(
                    message.channel,
                    response,
                )

            except Exception as error:
                logger.exception(
                    "Failed to process mention"
                )

                await message.reply(
                    f"⚠️ {error}"
                )

    await bot.process_commands(message)


# ============================================
# AI Command
# ============================================

@bot.command(
    name="ai",
    help="Talk with Nexus AI.",
)
async def ai(ctx, *, message):
    async with ctx.typing():
        try:
            response = await engine.ask(
                user_id=ctx.author.id,
                message=message,
            )

            await send_long_message(
                ctx,
                response,
            )

        except Exception as error:
            logger.exception(
                "AI command failed"
            )

            await ctx.send(
                f"⚠️ {error}"
            )


# ============================================
# Memory Command
# ============================================

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


# ============================================
# Start Nexus
# ============================================

async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing."
        )

    runner = await start_health_server()

    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())