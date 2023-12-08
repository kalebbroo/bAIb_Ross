import discord
from discord.ext import commands
from io import BytesIO
import base64
import os
import requests
from dotenv import load_dotenv

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='+', intents=intents)

bot.ran_prompt, bot.ran_negative = None, None

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# TODO: Fix the showcase logic to work with the new API and move it to a cog
async def showcase(bot, image_data, info, channel_id):
    # Convert the base64 image data to bytes
    image_bytes = base64.b64decode(image_data)
    image_file = discord.File(BytesIO(image_bytes), filename="upscaled_image.png")

    # Create an embed with the image information
    embed = discord.Embed(title="Upscaled Image", description="Here's an upscaled image!")
    embed.add_field(name="Steps", value=info['steps'], inline=True)
    embed.add_field(name="Seed", value=info['seed'], inline=True)
    embed.add_field(name="Model", value=info['model'], inline=True)
    embed.add_field(name="Prompt", value=info['prompt'], inline=True)
    embed.add_field(name="Negative", value=info['negative'], inline=True)
    embed.set_image(url="attachment://upscaled_image.png")

    # Get the showcase channel
    channel = bot.get_channel(channel_id)

    # Send the embed to the showcase channel
    message = await channel.send(file=image_file, embed=embed)

    # Start a new thread for the image
    thread = await message.start_thread(name="Discussion for upscaled image")

    return thread

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
    fmt  = await bot.tree.sync()
    print(f"synced {len(fmt)} commands")
    print(f"Loaded: {len(bot.cogs)} cogs")
    bot.ran_prompt, bot.ran_negative = await generate_random_prompt()
    bot.payloads = {}
    bot.image_timestamps = {}


if __name__ == "__main__":
    bot.run(BOT_TOKEN)