import discord
from discord.ext import commands
from discord import app_commands
from baib_ross import showcase
from config import SHOWCASE_ID
import requests
from typing import List
import asyncio
import time
import aiohttp


async def model_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    # Make a GET request to the API to fetch the list of available models
    response = requests.get('http://localhost:7860/sdapi/v1/sd-models')

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        models = response.json()

        # Extract the model names and create a list of choices
        return [
            app_commands.Choice(name=model['model_name'], value=model['model_name'])
            for model in models if current.lower() in model['model_name'].lower()
        ]
    else:
        return []




class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.eta_task = None


    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready!")


        


    @app_commands.command(name="dream", description="Generate an image using the Stable Diffusion API")
    @app_commands.describe(prompt = "Enter the text prompt that you want the image to be generated from")
    @app_commands.describe(negative = "Enter any negative prompts to avoid certain elements in the image")
    @app_commands.autocomplete(model=model_autocomplete)
    @app_commands.describe(steps = "Specify the number of steps for the diffusion process")
    @app_commands.describe(seed = "Provide a seed for the random number generator to ensure reproducibility")
    @app_commands.describe(sampler_name = "Choose the sampling method for the diffusion process")
    @app_commands.describe(cfg_scale = "Specify the configuration scale for the model")
    @app_commands.describe(face_restoration = "Choose whether to apply face restoration to the generated image")
    @app_commands.describe(denoising_strength = "Specify the strength of denoising to be applied to the generated image")
    async def dream(self, interaction: discord.Interaction, prompt: str = None, negative: str = "NSFW", model: str = None, steps: int = 10,
                    seed: int = -1, sampler_name: str = "DPM++ 2S a Karras", cfg_scale: int = 7, face_restoration: bool = False, denoising_strength: float = 0.7):
        await interaction.response.defer()
        await interaction.followup.send(f"Creating image from prompt: {prompt}", ephemeral=True)

        # Call the text2image function with the provided options
        payload = self.bot.get_cog('Text2Image').create_payload(prompt, negative, steps, seed, cfg_scale, 512, 512, False,)

        # Start the ETA task
        self.eta_task = asyncio.ensure_future(self.update_eta(interaction))

        image_data = await self.bot.get_cog('Text2Image').txt2image(payload)
        image_file = await self.bot.get_cog('Text2Image').pull_image(image_data)
        # Create an instance of the ImageView
        buttons = self.bot.get_cog('Buttons').ImageView(interaction, image_data['images'], payload)
        self.bot.get_cog('Buttons').payload = payload

        embed = await self.create_embed(interaction, prompt, negative, steps, seed, cfg_scale)
        await interaction.channel.send(embed=embed, file=image_file, view=buttons)

        # Store the payload in the Buttons cog
        self.bot.get_cog('Buttons').payload = payload

        print(f"{interaction.user.display_name} Dreampt of {prompt}")

        # Cancel the ETA task
        if self.eta_task and not self.eta_task.done():
            self.eta_task.cancel()
            self.eta_task = None

    async def update_eta(self, interaction):
        start_time = time.time()
        eta_message = None
        while True:
            eta = await get_eta()
            if eta > 0.0 or time.time() - start_time > 30:
                if eta_message:
                    await eta_message.edit(content=f"Estimated Generation Time: {int(eta)} seconds")
                else:
                    eta_message = await interaction.channel.send(f"Estimated Generation Time: {int(eta)} seconds")
            if eta <= 0.0 or time.time() - start_time > 30:
                break
            await asyncio.sleep(0.5)


    async def create_embed(self, interaction, prompt, negative, steps, seed, cfg_scale, width=512, height=512):
        user = interaction.user
        title = f"Generated by {user.name}"
        description = f"Prompt: {prompt}\nNegative: {negative}"
        footer_text = f"Steps: {steps}, Seed: {seed}, CFG Scale: {cfg_scale}, Width: {width}, Height: {height}"

        embed = discord.Embed(
            title=title,
            description=description,
            color=6301830
        )
        embed.set_image(url="attachment://temp.png")
        embed.set_footer(text=footer_text)
        embed.set_author(name=user.name, icon_url=user.avatar.url)

        return embed


async def get_eta():
    url = "http://localhost:7860/sdapi/v1/progress"
    params = {"skip_current_image": "false"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                eta = data["eta_relative"]
                return eta
            else:
                return None





async def setup(bot):
    await bot.add_cog(Commands(bot))
    