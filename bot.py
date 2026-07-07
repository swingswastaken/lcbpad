import discord
from discord.ext import commands

from config import MODE, GUILD_ID

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    if MODE == "test":
        if GUILD_ID is None:
            raise RuntimeError("GUILD_ID is required in test mode.")

        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"Logged in as {bot.user} (TEST MODE)")
    else:
        await bot.tree.sync()
        print(f"Logged in as {bot.user} (GLOBAL MODE)")


# Import commands so they register with the bot
import commands.skills
import commands.clash
