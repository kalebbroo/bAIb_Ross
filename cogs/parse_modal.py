import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
import openai
from config import GPT_KEY
from payload import Payload
import requests
import re

class ParseModal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def parse_modal(self, interaction, prompt, styles, model, settings):
            # Split prompt and negative from modal text
            main_focus = prompt.split("[Main Focus]: ")[1].split(" [Background / Atmosphere]:")[0]
            background_atmosphere = prompt.split("[Background / Atmosphere]: ")[1].split(" [Style / Quality]:")[0]
            style_quality = prompt.split("[Style / Quality]: ")[1].split(" [Negative]:")[0]
            negative = prompt.split("[Negative]:")[1].replace("'", "")
            prompt = [main_focus, background_atmosphere, style_quality, negative]

            # split styles
            #Todo: make the logic
            styles = styles

            # Make sure there is only 1 model
            #Todo: make the logic 
            model_list = self.bot.model_list
            model = re.sub("^[0-9]+: ", "", model)
            for item in model_list:
                if item == model:
                    await interaction.channel.send(f"Setting model to {model}. This may take a few seconds. Please wait...")
                    await self.change_ckpt(interaction, model)
                    await interaction.channel.send(f"Model set to {model}.")
                else:
                    default = "disneyPixarCartoon_v10"
                    await interaction.channel.send(f"Only one model can be set at a time. Defaulting to {default}.")
                    print(model)
                    break

            # split the settings and check for valid values
            steps = settings.split("[Steps]: ")[1].split(", ")[0]
            seed = settings.split("[Seed]: ")[1].split(", ")[0]
            cfg_scale = settings.split("[CFG Scale]: ")[1].split(", ")[0]
            width = settings.split("[Width]: ")[1].split(", ")[0]
            height = settings.split("[Height]: ")[1]

            batch_size = 4

            return prompt, model, steps, seed, cfg_scale, batch_size

    async def change_ckpt(self, interaction, model):
        url = "http://127.0.0.1:7860" # or your URL
        opt = requests.get(url=f'{url}/sdapi/v1/options')
        opt_json = opt.json()
        opt_json['sd_model_checkpoint'] = model
        requests.post(url=f'{url}/sdapi/v1/options', json=opt_json)



async def setup(bot):
    await bot.add_cog(ParseModal(bot))