from discord.ext import commands
from discord.ext.commands import Bot as BotBase
import requests
import json


class text2image(commands.Cog):
    bot: BotBase

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def txt2image(prompt, negative, steps, seed, cfg_scale, width, height):
        # Define the URL and headers for the API request
        url = "http://localhost:7860/sdapi/v1/txt2img"
        headers = {"Content-Type": "application/json"}

        # Define the data to be sent in the API request
        data = {
            "prompt": prompt,
            "negative_prompt": negative,
            "steps": steps,
            "seed": seed,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height
        }

        try:
            # Send the API request
            response = requests.post(url, headers=headers, data=json.dumps(data))

            # If the request was successful, return the response data
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            # If there was an error with the request, print the error and return None
            print(f"RequestException: {e}")
            return None


@commands.Cog.listener()
async def setup(bot: BotBase) -> None:
    # Add the text2image cog to the bot
    bot.add_cog(text2image(bot))
