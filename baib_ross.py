import discord
from discord.ext import commands
from discord import app_commands
from io import BytesIO
import base64
import requests
import json
from config import TOKEN
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

def upscale_image(image_path):
    url = "http://localhost:7860/sdapi/v1/img2img"  # replace with the correct URL
    headers = {"Content-Type": "application/json"}  # replace with the correct headers

    # Read the image file and convert it to base64
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

    data = {
        "image": encoded_string
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None


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

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await load_extensions()


if __name__ == "__main__":
    bot.run(TOKEN)