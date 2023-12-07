from discord.ext import commands
from discord import app_commands, Embed, Colour
import base64
from aiohttp import ClientSession
import websockets
import json
import base64
from PIL import Image
from io import BytesIO
import discord
import logging
import aiohttp

# THIS IS A TEST COG FOR THE NEW API WHOLE COG WILL BE DELETED ONCE THE NEW API IS IMPLEMENTED

class GenerateImage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_id = ""

    async def get_session(self, bot):
        api_call = bot.get_cog("APICalls")
        await api_call.get_session()
        self.session_id = api_call.session_id

    async def url_to_base64(self, url: str) -> str:
        """
        Fetches an image from a URL and converts it to a base64 string.

        :param url: The URL of the image.
        :type url: str
        :return: The base64 string representation of the image.
        :rtype: str
        """
        async with ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                base64_data = base64.b64encode(data).decode("utf-8")
                return base64_data


    @app_commands.command(name='test', description='test generate image')
    @app_commands.describe(prompt='add_your_prompt', negative='add_your_negative_prompt', image='add_your_image_url')
    async def test(self, interaction, prompt: str, negative: str, image: str = None):
        """
        Generates an image based on the provided prompt and negative prompt.
        
        :param interaction: The interaction object from the Discord API.
        :param prompt: The prompt for the image generation.
        :param negative: The negative prompt for the image generation.
        """
        await interaction.response.defer()
        # Get a new session ID
        await self.get_session(self.bot)
        await self.build_payload(self.bot, interaction, prompt, negative, image)

    async def build_payload(self, bot, interaction, prompt: str, negativeprompt: str, init_img: str = None) -> None:
        """
        Creates an API payload based on user input and triggers the image generation process.

        This method takes user input to create a payload using a Payload instance, 
        then calls the text_to_image method to initiate the image generation process.
        After generating the image, it stores the payload in the interaction.client.payloads dictionary 
        using the user's ID as the key.

        :param interaction: Interaction object representing the command invocation context.
        :type interaction: Union[Context, SlashContext]
        :param prompt: The text prompt based on which the image will be generated.
        :type prompt: str
        :param negativeprompt: Negative prompt for the image generation.
        :type negativeprompt: str
        :return: None
        """
        # Convert the image URL to base64 if provided
        init_img_base64 = None
        if init_img:
            init_img_base64 = await self.url_to_base64(init_img)
            if not init_img_base64:
                print("Failed to fetch or convert the image from the given URL.")
                return

        # Create payload with additional parameters
        api_call = bot.get_cog("APICalls")
        payload = api_call.create_payload(
            session_id=self.session_id if self.session_id else api_call.session_id,
            prompt=prompt,
            negativeprompt=negativeprompt,
            model="turbovisionxlSuperFastXLBasedOnNew_tvxlV20Bakedvae.safetensors",
            width=768,
            height=1344,
            cfgscale=2.5,
            steps=6,
            seed=-1,
            init_image=init_img_base64,
            sampler="dpmpp_sde",
            scheduler="karras",
        )
        
        await self.generate_image(bot, interaction, payload)
        interaction.client.payloads[str(interaction.user.id)] = payload


    async def generate_image(self, bot, interaction, payload):
        api_call = bot.get_cog("APICalls")
        await api_call.aiohttp_call_collect(interaction, payload)
        



async def setup(bot):
    await bot.add_cog(GenerateImage(bot))