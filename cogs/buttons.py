import os
import discord
from discord.ext import commands
from discord import ButtonStyle, Interaction, ui
from discord.ui import Button, View, Select, Modal, TextInput
from io import BytesIO
from PIL import Image
from datetime import datetime



class Buttons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    class ImageView(View):
        def __init__(self, interaction, image_urls, payload):
            super().__init__()
            self.image_urls = image_urls
            self.payload = payload

            # Add buttons to the view with custom ids
            self.add_item(Button(style=ButtonStyle.success, label="Regenerate", custom_id="regenerate", row=1))
            self.add_item(Button(style=ButtonStyle.primary, label="Upscale", custom_id="upscale", row=1))
            self.add_item(Button(style=ButtonStyle.danger, label="Delete", custom_id="delete", row=1))
            self.add_item(Button(style=ButtonStyle.secondary, label="Generate From Source Image", custom_id="choose_img", row=2))


    class SelectMenuView(discord.ui.View):
        def __init__(self, select_menu):
            super().__init__()
            self.add_item(select_menu)


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
            embed=discord.Embed(title=(f"Generating images from {self.values[0]}..."), color=0xff0000)
            await interaction.channel.send(embed=embed)
            # Get the selected image file
            selected_image_file = self.values[0]
            self.payload.update({"init_image": selected_image_file})

            # Generate more images from the selected image
            print(f"Payload before create_img2img: {self.payload}")
            await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)

            buttons = self.bot.get_cog('Buttons').ImageView(interaction, self.payload)
            #TODO: Add buttons to the message

    class UpscaleSelect(Select):
        def __init__(self, bot, image_files):
            self.bot = bot
            options = []
            for i, image_file in enumerate(image_files):
                # Create a SelectOption for each image file
                option = discord.SelectOption(label=f"Image {i+1}", value=image_file)
                options.append(option)

            super().__init__(placeholder='Choose the image you wish to upscale', options=options)

        async def callback(self, interaction: Interaction):
            await interaction.response.defer()
            # Get the selected image file
            selected_image_file = self.values[0]

            # Call the upscale_image function to upscale the image
            upscaled_image_path = await self.bot.get_cog('Image2Image').upscale_image(selected_image_file, interaction)

            # Display the upscaled image
            with open(upscaled_image_path, 'rb') as f:
                upscaled_image = discord.File(f)
                await interaction.channel.send(file=upscaled_image)

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            button_id = interaction.data["custom_id"]

            # Get the timestamp from the message
            username = interaction.user.name
            date_string, time_string = self.bot.image_timestamps[username]

            # Get the username and the first three words of the prompt
            prompt = interaction.client.payloads[str(interaction.user.id)]['prompt']
            prompt_words = prompt.split()[:3]
            prompt_string = "_".join(prompt_words)

            # Get the path to the recently generated images
            image_folder_path = os.path.join("cached_images", date_string, time_string)

            match button_id:
                case "choose_img":
                    await interaction.response.defer()
                    # Get the recently generated images
                    image_files = [os.path.join(image_folder_path, image_file) for image_file in os.listdir(image_folder_path)]
                    select_menu = self.ImageSelect(self.bot, image_files, self.payload)
                    select_menu_view = self.SelectMenuView(select_menu)
                    await interaction.channel.send("Select an image to generate more from.", view=select_menu_view)
                case "upscale":
                    await interaction.response.defer()
                    # Get the recently generated images
                    image_files = [os.path.join(image_folder_path, image_file) for image_file in os.listdir(image_folder_path)]
                    select_menu = self.UpscaleSelect(self.bot, image_files)
                    select_menu_view = self.SelectMenuView(select_menu)
                    await interaction.channel.send("Select an image to upscale so you can save it.", view=select_menu_view)
                case "regenerate":
                    await interaction.response.defer()
                    await interaction.followup.send("Regenerating...")
                    #TODO: get the payload
                    await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)
                case "delete":
                    await interaction.response.defer()
                    # Delete the message
                    await interaction.message.delete()
                    await interaction.response.channel.send("Embed deleted", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Buttons(bot))