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
                await message.reply(f"❌ {error}")

    # Keep commands like !ping working
    await bot.process_commands(message)

# Simple test command
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

@bot.command()
async def ai(ctx, *, message):

    # Tell the user the bot is thinking...
    async with ctx.typing():

        try:
            response = await ask_ai(message, ctx.author.id)
            await ctx.send(response)

        except Exception as error:
            await ctx.send(f"❌ Error:\n```{error}```")

# Start the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
