import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='+', intents=intents)

bot.ran_prompt, bot.ran_negative = None, None

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

async def showcase_buttons():
    # Refresh Showcase Buttons
    showcase_cog = bot.get_cog('Showcase')
    if showcase_cog:
        for guild in bot.guilds:
            showcase_channel = discord.utils.get(guild.channels, name='showcase', type=discord.ChannelType.text)
            if showcase_channel:
                try:
                    # Fetch recent messages from the showcase channel
                    async for message in showcase_channel.history(limit=100):  # Adjust limit as needed
                        if message.author == bot.user and message.embeds:
                            voting_buttons = showcase_cog.VotingButtons(showcase_cog, message.id)
                            await message.edit(view=voting_buttons)
                except Exception as e:
                    print(f"Failed to refresh Showcase buttons in guild {guild.name}: {e}")
            else:
                print(f"Showcase channel not found in guild {guild.name}.")

async def generate_random_prompt():
    ai = bot.get_cog("AIPromptGenerator")
    random_prompt, random_negative = await ai.gen_random_prompt()
    return random_prompt, random_negative

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await load_extensions()
    fmt = await bot.tree.sync()
    print(f"synced {len(fmt)} commands")
    print(f"Loaded: {len(bot.cogs)} cogs")
    bot.ran_prompt, bot.ran_negative = await generate_random_prompt()
    bot.payloads = {}
    bot.image_timestamps = {}
    await showcase_buttons()

if __name__ == "__main__":
    bot.run(BOT_TOKEN)