import discord
from discord.ext import commands
from io import BytesIO
import base64
from config import TOKEN
import os
import requests

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)


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

async def model_autocomplete(current: str = ""):
    # Make a GET request to the API to fetch the list of available models
    response = requests.get('http://localhost:7860/sdapi/v1/sd-models')

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        models = response.json()

        # Extract the model names and create a list of choices
        model_list = [model['model_name'] for model in models if current.lower() in model['model_name'].lower()]
        # Create a formatted string with each model on a new line, preceded by its number
        formatted_list = "\n".join(f"{i+1}. {model}" for i, model in enumerate(model_list))
        return formatted_list
    else:
        return ""

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await load_extensions()
    fmt  = await bot.tree.sync()
    print(f"synced {len(fmt)} commands")
    print(f"Loaded: {len(bot.cogs)} cogs")
    bot.model_list = await model_autocomplete()
    bot.payloads = {}
    bot.image_timestamps = {}
    #print(model_list)



if __name__ == "__main__":
    bot.run(TOKEN)