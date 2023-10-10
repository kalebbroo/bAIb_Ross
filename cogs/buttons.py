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
        def __init__(self, bot, interaction, payload, message_id=None):
            super().__init__(timeout=180)
            self.bot = bot
            self.payload = payload
            self.message_id = message_id


        @discord.ui.button(style=ButtonStyle.success, label="Regenerate", custom_id="regenerate", row=1)
        async def regenerate(self, interaction, button):
            await interaction.response.defer()
            await interaction.followup.send("Regenerating...", ephemeral=True)
            await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)

        @discord.ui.button(style=ButtonStyle.primary, label="Upscale", custom_id="upscale", row=1)
        async def upscale(self, interaction, button):
            await interaction.response.defer()
            try:
                message_info = self.bot.get_cog('APICalls').message_data.get(self.message_id)  # Retrieve the stored info
                print(f"message_info: {message_info}")

                # Initialize image_files as an empty list
                image_files = []

                if message_info:
                    payload = message_info.get('payload')
                    user_id = message_info.get('user_id')
                    image_files = message_info.get('image_files', [])

                if not image_files:
                    await interaction.followup.send("No images found to upscale.", ephemeral=True)
                    return

                select_menu = self.UpscaleSelect(self.bot, image_files)
                await interaction.channel.send("Select an image to upscale so you can save it.", view=select_menu)

            except Exception as e:
                print(f"An exception occurred in the upscale button: {e}")

        @discord.ui.button(style=ButtonStyle.danger, label="Delete", custom_id="delete", row=1)
        async def delete(self, interaction, button):
            # Delete the message
            await interaction.response.channel.send("Embed deleted", ephemeral=True)
            await interaction.message.delete()

        @discord.ui.button(style=ButtonStyle.secondary, label="Generate From Source Image", custom_id="choose_img", row=2)
        async def choose_img(self, interaction, button):
            await interaction.response.defer()
            try:
                message_data = self.bot.get_cog('APICalls').message_data.get(self.message_id)  # Retrieve the stored info

                print(f"Message ID in buttons: {self.message_id}")
                print(f"Message Data in buttons: {self.bot.get_cog('APICalls').message_data}")

                # Initialize image_files as an empty list
                #image_files = []

                if message_data:
                    payload = message_data.get('payload')
                    user_id = message_data.get('user_id')
                    image_files = message_data.get('image_files', [])
                    print(f"\nImage files from button press: {image_files}\n")

                if not image_files:
                    await interaction.followup.send("No images found to upscale.", ephemeral=True)
                    return
                            
                select_menu = Buttons.ImageSelect(self.bot, image_files, self.payload)
                view = discord.ui.View()
                view.add_item(select_menu)
                await interaction.channel.send("Select an image to generate more from.", view=view)
            except Exception as e:
                print(f"An exception occurred in the choose_img button: {e}")


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

        # TODO: Test these parameters
        """Most Likely Essential Parameters:
            lastparam_input_model
            selected_model
            lastparam_input_width
            lastparam_input_height

        Potentially Optional but Important:
            lastparam_input_aspectratio
            lastparam_input_prompt"""

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
            super().__init__(placeholder='Choose an image to use as a reference', options=options)

        async def callback(self, interaction):
            await interaction.response.defer()
            # Get the selected image file
            selected_image_path = self.values[0]

        # TODO: Add the option to use different settings and prompt
            
            # Convert the image to Base64
            with open(selected_image_path, "rb") as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Update the payload
            self.payload.update({"initimage": base64_image})
            # TODO: maybe add another peram init_image_creativity

            # Generate more images from the selected image
            await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)

async def setup(bot):
    await bot.add_cog(Buttons(bot))