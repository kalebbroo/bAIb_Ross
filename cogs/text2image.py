#text2image functions
from discord.ext import commands
from discord import app_commands
import requests
import json


class text2image(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot

    def txt2image(prompt, negative, steps, seed, cfg_scale, width, height):
    url = "http://localhost:7860/sdapi/v1/txt2img"  # replace with the correct URL
    headers = {"Content-Type": "application/json"}  # replace with the correct headers
    data = {
        "prompt": prompt,
        "negative_prompt": negative,
        "steps": steps,
        "seed": seed,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(text2image(bot))