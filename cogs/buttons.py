import os
import discord
from discord.ext import commands
from discord import ButtonStyle, Interaction, ui
from discord.ui import Button, View, Select, Modal, TextInput
from io import BytesIO
from PIL import Image
from datetime import datetime
import base64

class Buttons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """Buttons for the image grid embed"""

    class ImageButtons(View):
        def __init__(self, bot, interaction, payload):
            super().__init__(timeout=180)
            self.bot = bot
            self.payload = payload
            self.unique_id = payload.get('unique_id')

        @discord.ui.button(style=ButtonStyle.success, label="Regenerate", custom_id="regenerate", row=1)
        async def regenerate(self, interaction, button):
            await interaction.response.defer()
            await interaction.followup.send("Regenerating...", ephemeral=True)
            await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)

        @discord.ui.button(style=ButtonStyle.primary, label="Upscale", custom_id="upscale", row=1)
        async def upscale(self, interaction, button):
            await interaction.response.defer()

            # Use unique_id to fetch the image files
            image_files = self.bot.get_cog('APICalls').image_paths.get(self.unique_id, [])
            
            if not image_files:
                await interaction.followup.send("No images found to upscale.", ephemeral=True)
                return

            select_menu = self.UpscaleSelect(self.bot, image_files)
            await interaction.channel.send("Select an image to upscale so you can save it.", view=select_menu)

        @discord.ui.button(style=ButtonStyle.danger, label="Delete", custom_id="delete", row=1)
        async def delete(self, interaction, button):
            # Delete the message
            await interaction.message.delete()
            await interaction.response.channel.send("Embed deleted", ephemeral=True)

        @discord.ui.button(style=ButtonStyle.secondary, label="Generate From Source Image", custom_id="choose_img", row=2)
        async def choose_img(self, interaction, button):
            await interaction.response.defer()

            # Use unique_id to fetch the image files
            image_files = self.bot.get_cog('APICalls').image_paths.get(self.unique_id, [])
            
            select_menu = self.ImageSelect(self.bot, image_files, self.payload)
            await interaction.channel.send("Select an image to generate more from.", view=select_menu)


    """Selecet Menus for choosing an img2img or upscale"""

    # Select Menu for choosing an image to upscale
    class UpscaleSelect(Select):
        def __init__(self, bot, image_files):
            self.bot = bot
            options = []

            for i, image_file in enumerate(image_files):
                # Create a SelectOption for each image file
                option = discord.SelectOption(label=f"Image {i+1}", value=image_file)
                options.append(option)

            super().__init__(placeholder='Choose the image you wish to upscale', options=options)

        async def callback(self, interaction):
            await interaction.response.defer()
            # Get the selected image file
            selected_image_path = self.values[0]

            # Convert the image to Base64
            with open(selected_image_path, "rb") as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')

            # Create or update the payload
            payload = {
                "initimage": base64_image
                # ... (Any other parameters you need)
            }

            # Call the API method to upscale the image
            upscaled_image_path = await self.bot.get_cog('APICalls').call_collect(interaction, payload)

            # Display the upscaled image
            with open(upscaled_image_path, 'rb') as f:
                upscaled_image = discord.File(f)
                await interaction.channel.send(file=upscaled_image)

    class ImageSelect(Select):
        def __init__(self, bot, image_files, payload):
            self.bot = bot
            self.payload = payload
            options = []
            for i, image_file in enumerate(image_files):
                # Create a SelectOption for each image file
                option = discord.SelectOption(label=f"Image {i+1}", value=image_file)
                options.append(option)
            super().__init__(placeholder='Choose an image to use as a reference to generate more images', options=options)

        async def callback(self, interaction):
            await interaction.response.defer()
            # Get the selected image file
            selected_image_path = self.values[0]
            
            # Convert the image to Base64
            with open(selected_image_path, "rb") as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Update the payload
            self.payload.update({"initimage": base64_image})

            # Generate more images from the selected image
            await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)

            embed = discord.Embed(title=f"Generating images from {selected_image_path}...", color=0xff0000)
            await interaction.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Buttons(bot))