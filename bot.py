"""
Project Nexus

Discord Bot Entry Point
"""

import discord
from discord.ext import commands

from config import DISCORD_TOKEN
from ai.engine import engine

from database.database import setup_database
from database.facts import get_facts


# ============================================
# Discord Intents
# ============================================

intents = discord.Intents.default()
intents.message_content = True


# ============================================
# Bot
# ============================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


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
            name="the Nexus"
        )
    )

    print("Project Nexus is online.")


@bot.event
async def on_message(message):

    if message.author.bot:
        return

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
                    message=user_message
                )

                await message.reply(response)

            except Exception as error:

                await message.reply(
                    f"⚠️ {error}"
                )

    await bot.process_commands(message)


# ============================================
# Commands
# ============================================

@bot.command()
async def ai(ctx, *, message):

    async with ctx.typing():

        try:

            response = await engine.ask(
                user_id=ctx.author.id,
                message=message
            )

            await ctx.send(response)

        except Exception as error:

            await ctx.send(
                f"⚠️ {error}"
            )


@bot.command()
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

    await ctx.send(
        f"## 🧠 Things I remember about you:\n{text}"
    )


# ============================================
# Start Bot
# ============================================

if __name__ == "__main__":

    bot.run(DISCORD_TOKEN)
