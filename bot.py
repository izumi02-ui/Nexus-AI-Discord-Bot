import discord
from discord.ext import commands

from config import DISCORD_TOKEN

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
    print("Nexus AI is now online!")
    print("=" * 40)

# Simple test command
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Start the bot
bot.run(DISCORD_TOKEN)
