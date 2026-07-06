from memory_manager import process_message
from database import get_facts
from database import setup_database

import discord
from discord.ext import commands

from config import DISCORD_TOKEN
from openai_client import ask_ai

# Enable the required Discord intents
intents = discord.Intents.default()
intents.message_content = True

# Create the bot
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# Runs when the bot starts
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

    print("Nexus AI is ready!")

@bot.event
async def on_message(message):

    # Ignore messages from bots
    if message.author.bot:
        return

    # Check if the bot was mentioned
    if bot.user in message.mentions:

        # Show "typing..."
        async with message.channel.typing():

            # Remove the bot mention from the message
            user_message = message.content.replace(f"<@{bot.user.id}>", "")
            user_message = user_message.replace(f"<@!{bot.user.id}>", "").strip()

            if not user_message:
                await message.reply("Hi! 👋 What can I help you with?")
                return

            try:
                response = await ask_ai(user_message, message.author.id)
                await message.reply(response)

            except Exception as error:
                await message.reply(f"X {error}")

    # Keep commands like !ping working
    await bot.process_commands(message)

# Simple test command
@bot.command()
async def ai(ctx, *, message):

    async with ctx.typing():

        try:
            process_message(ctx.author.id, message)

            response = await ask_ai(message, ctx.author.id)

            await ctx.send(response)

        except Exception as error:

    error_text = str(error)

    if "insufficient_quota" in error_text:
        await ctx.send(
            "⚠️ **Nexus AI is currently offline.**\n\n"
            "The AI service has run out of API quota.\n"
            "Please contact **Izumi** if the problem continues."
        )

    else:
        await ctx.send(
            f"⚠️ Something went wrong.\n```{error}```"
        )


@bot.command()
async def memory(ctx):

    facts = get_facts(ctx.author.id)

    if not facts:
        await ctx.send("🧠 I don't remember anything about you yet.")
        return

    text = "\n".join(f"• {fact}" for fact in facts)

    await ctx.send(
        f"## 🧠 Things I remember about you:\n{text}"
    )


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
