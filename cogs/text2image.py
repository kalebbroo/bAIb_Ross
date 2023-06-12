import os
import discord
from discord.ext import commands
from discord.ext.commands import Bot as BotBase
import aiohttp
from io import BytesIO
from PIL import Image
import base64
from payload import Payload
from datetime import datetime


class Text2Image(commands.Cog):
    bot: BotBase

    def __init__(self, bot):
        self.bot = bot

    async def txt2img_payload(self, bot, interaction, prompt, negative_prompt):
        payload_instance = Payload(bot)
        payload = await payload_instance.create_payload(prompt, negative_prompt)
        await self.text2image(payload)
        interaction.client.payloads[str(interaction.user.id)] = payload

        
    

    @staticmethod
    async def txt2image(payload):
        url = "http://localhost:7860/sdapi/v1/txt2img"
        headers = {"Content-Type": "application/json"}

        #print(f"Payload: {payload}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                else:
                    print(f"Error: {response.status}")
                    response_data = {}
                return response_data, payload
                
    async def pull_image(self, response_data, interaction):
        # Get the list of images from the response
        images_data = response_data['images']

        # Decode each image and convert it to a PIL Image object
        images = [Image.open(BytesIO(base64.b64decode(image_data))) for image_data in images_data]

        # Determine the grid size based on the number of images
        grid_size = int(len(images) ** 0.5)

        # Create a new image of the appropriate size to hold the grid
        grid_image = Image.new('RGB', (grid_size * images[0].width, grid_size * images[0].height))

        # Get the current date and time
        now = datetime.now()
        date_string = now.strftime("%Y-%m-%d")
        time_string = now.strftime("%H-%M-%S")

        # Get the username and the first three words of the prompt
        username = interaction.user.name
        prompt = interaction.client.payloads[str(interaction.user.id)]['prompt']
        prompt_words = prompt.split()[:3]
        prompt_string = "_".join(prompt_words)

        # Place each image into the grid and save each image individually
        for i, image in enumerate(images):
            row = i // grid_size
            col = i % grid_size
            grid_image.paste(image, (col * image.width, row * image.height))

            # Create the directory
            os.makedirs(f"cached_images/{date_string}/{time_string}", exist_ok=True)

            # Save the image
            image_path = os.path.join("cached_images", date_string, time_string, f"{username}_{prompt_string}_{i}.png")
            image.save(image_path)

            # After sending the message with the images
            self.bot.image_timestamps[username] = date_string, time_string # Store the timestamp in the dictionary
            print(f"Stored timestamp {time_string} {date_string} for {username}")

        # Save the grid image to a BytesIO object
        image_file = BytesIO()
        grid_image.save(image_file, format='PNG')
        image_file.seek(0)

        # Wrap the BytesIO object in a File object for sending via Discord
        image_file = discord.File(image_file, filename="temp.png")

        return image_file



        
async def setup(bot):
    await bot.add_cog(Text2Image(bot))

