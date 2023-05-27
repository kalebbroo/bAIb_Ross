import requests
import json
import discord
import os
from discord import Activity, ActivityType, Intents
from discord.ext.commands import Bot
from discord import File
from io import BytesIO
from pathlib import Path
import base64
import asyncio
import contextlib
from os import listdir
from config import TOKEN

class bAIb_Ross(Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=Intents.default())
        self.token = TOKEN

    async def on_connect(self):
        await self.change_presence(activity=Activity(type=ActivityType.watching, name="Slash Commands"))

    async def setup_hook(self):
        cogs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cogs")
        for file in os.listdir(cogs_dir):
            if file.endswith(".py") and not file.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                except Exception as e:
                    print(f"Error loading {file[:-3]} cog: {e}")

    async def main(self) -> None:
        await self.setup_hook()
        async with self:
            await self.start(self.token)

    def starter(self):
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self.main())

if __name__ == "__main__":
    bot = bAIb_Ross()
    bot.starter()


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


async def save_image_to_showcase_channel(bot, image_data, info, channel_id):
    # Convert the base64 image data to bytes
    image_bytes = base64.b64decode(image_data)
    image_file = File(BytesIO(image_bytes), filename="upscaled_image.png")

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