import os
import discord
from discord.ext import commands
from discord import ButtonStyle, Interaction, ui
from discord.ui import Button, View, Select, Modal, TextInput
import base64
from io import BytesIO
from PIL import Image




class Buttons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.payload = None


    class ImageView(View):
        def __init__(self, ctx, image_urls, payload):
            super().__init__()
            self.ctx = ctx
            self.image_urls = image_urls
            self.payload = payload

            # Add buttons to the view with custom ids
            self.add_item(Button(style=ButtonStyle.success, label="Regenerate", custom_id="regenerate", row=1))
            self.add_item(Button(style=ButtonStyle.primary, label="Upscale", custom_id="upscale", row=1))
            self.add_item(Button(style=ButtonStyle.danger, label="Delete", custom_id="delete", row=1))
            self.add_item(Button(style=ButtonStyle.secondary, label="Pick Source Image", custom_id="choose_img", row=2))
            self.add_item(Button(style=ButtonStyle.secondary, label="Edit", custom_id="edit", row=2))
            self.add_item(Button(style=ButtonStyle.secondary, label="AI Prompt Generator", custom_id="ai_prompt", row=2))


    class SelectMenuView(discord.ui.View):
        def __init__(self, select_menu):
            super().__init__()
            self.add_item(select_menu)


    class ImageSelect(Select):
        def __init__(self, bot, image_files, payload):
            self.bot = bot
            self.payload = payload
            options = []
            for image_file in image_files:
                # Create a SelectOption for each image file
                option = discord.SelectOption(label=os.path.basename(image_file), value=image_file)
                options.append(option)

            super().__init__(placeholder='Images are labeled 0-3 from left to right', options=options)


        async def callback(self, interaction):
            await interaction.response.defer()
            embed=discord.Embed(title=(f"Generating images from {self.values[0]}..."), color=0xff0000)
            await interaction.channel.send(embed=embed)
            # Get the selected image file
            selected_image_file = self.values[0]

            # Generate more images from the selected image
            print(f"Payload before create_img2img: {self.payload}")
            generated_images = await self.bot.get_cog('Image2Image').create_img2img(selected_image_file, interaction, self.payload)

            # Create a new embed with a grid of images
            embed = await self.bot.get_cog('Commands').create_embed(interaction, prompt="", negative="", 
                                                                    steps=60, seed=-1, cfg_scale=7, width=512, height=512)
        

            # Decode each image and convert it to a PIL Image object
            images = [image_data for image_data in generated_images]


            # Determine the grid size based on the number of images
            grid_size = int(len(images) ** 0.5)

            # Create a new image of the appropriate size to hold the grid
            grid_image = Image.new('RGB', (grid_size * images[0].width, grid_size * images[0].height))

            # Place each image into the grid and save each image individually
            for i, image in enumerate(images):
                row = i // grid_size
                col = i % grid_size
                grid_image.paste(image, (col * image.width, row * image.height))
                folder_path = "image_cache/new_images"
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                image_path = os.path.join(folder_path, f"new_images_{i}.png")
                image.save(image_path)

            # Save the grid image to a BytesIO object
            image_file = BytesIO()
            grid_image.save(image_file, format='PNG')
            image_file.seek(0)

            # Wrap the BytesIO object in a File object for sending via Discord
            image_file = discord.File(image_file, filename="temp.png")

            buttons = self.bot.get_cog('Buttons').ImageView(interaction, image_file, self.payload)
            await interaction.channel.send(embed=embed, file=image_file, view=buttons)



    class UpscaleSelect(Select):
        def __init__(self, bot, image_files):
            self.bot = bot
            options = []
            for image_file in image_files:
                # Create a SelectOption for each image file
                option = discord.SelectOption(label=os.path.basename(image_file), value=image_file)
                options.append(option)

            super().__init__(placeholder='Images are labeled 0-3 from left to right', options=options)


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



    class EditModal(Modal):
        def __init__(self, bot, payload):
            super().__init__(title="Edit Prompt")
            self.bot = bot
            self.payload = payload


            # Add a TextInput for the prompt
            self.prompt = TextInput(label='Prompt',
                                    style=discord.TextStyle.paragraph,
                                    placeholder='Enter your prompt here',
                                    min_length=1,
                                    max_length=2000,
                                    required=True)
            self.negative_prompt = TextInput(label='Negative Prompt',
                                            style=discord.TextStyle.paragraph,
                                            placeholder='Enter your prompt here',
                                            min_length=1,
                                            max_length=2000,
                                            required=True)
            # Add the TextInput components to the modal
            self.add_item(self.prompt)
            self.add_item(self.negative_prompt)



        async def on_submit(self, interaction):
            await interaction.response.defer()

            await interaction.channel.send("Generating images with new settings...")

            # Get the new values from the TextInput components
            new_prompt = self.prompt.value
            new_negative = self.negative_prompt.value

            # Update the payload with the new values
            self.payload['prompt'] = new_prompt
            self.payload['negative_prompt'] = new_negative

            # Regenerate the image using the updated payload
            response_data, payload = await self.bot.get_cog('Text2Image').txt2image(self.payload)
            image_file = await self.bot.get_cog('Text2Image').pull_image(response_data)


            buttons = self.bot.get_cog('Buttons').ImageView(interaction, response_data['images'], self.payload)

            # Create the embed
            embed = await self.bot.get_cog('Commands').create_embed(interaction, self.payload['prompt'], self.payload['negative_prompt'], 
                                                                    self.payload['steps'], self.payload['seed'], self.payload['cfg_scale'])
            # Update the message with the new image
            await interaction.channel.send(embed=embed, file=image_file, view=buttons)

            # Close the modal
            self.stop()





    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type == discord.InteractionType.component:
            button_id = interaction.data["custom_id"]
            payload = self.bot.get_cog('Buttons').payload
            print(f"Payload before update: {self.payload}")
            self.payload = payload
            print(f"Payload after update: {self.payload}")

            match button_id:
                case "choose_img":
                    await interaction.response.defer()
                    image_files = [os.path.join("image_cache", image_file) for image_file in os.listdir("image_cache")]
                    select_menu = self.ImageSelect(self.bot, image_files, payload)
                    select_menu_view = self.SelectMenuView(select_menu)
                    await interaction.channel.send("Select an image to generate more from.", view=select_menu_view)

                case "upscale":
                    await interaction.response.defer()
                    image_files = [os.path.join("image_cache", image_file) for image_file in os.listdir("image_cache")]
                    select_menu = self.UpscaleSelect(self.bot, image_files)
                    select_menu_view = self.SelectMenuView(select_menu)
                    await interaction.channel.send("Select an image to upscale so you can save it.", view=select_menu_view)


                case "regenerate":
                    await interaction.response.defer()
                    await interaction.followup.send("Regenerating...")
                    # Regenerate the image using the stored payload

                    response_data, payload = await self.bot.get_cog('Text2Image').txt2image(self.payload)
                    image_file = await self.bot.get_cog('Text2Image').pull_image(response_data)

                    buttons = self.bot.get_cog('Buttons').ImageView(interaction, response_data['images'], self.payload)

                    # Create the embed
                    embed = await self.bot.get_cog('Commands').create_embed(interaction, self.payload['prompt'], self.payload['negative_prompt'], 
                                                                            self.payload['steps'], self.payload['seed'], self.payload['cfg_scale'])
                    # Update the message with the new image
                    await interaction.channel.send(embed=embed, file=image_file, view=buttons)



                case "delete":
                    await interaction.response.defer()
                    # Delete the message
                    await interaction.message.delete()
                    await interaction.response.channel.send("Embed deleted", ephemeral=True)


                case "edit":
                    # Create the modal and open it
                    modal = self.EditModal(self.bot, self.payload)
                    await interaction.response.send_modal(modal)


                case "ai_prompt":
                    # Create the modal and open it
                    modal = self.EditModal(self.bot, self.payload)
                    await interaction.response.send_modal(modal)
                    




async def setup(bot):
    await bot.add_cog(Buttons(bot))