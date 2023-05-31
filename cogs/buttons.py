import os
import discord
from discord.ext import commands
from discord import ButtonStyle, Interaction
from discord.ui import Button, View, Select, Modal, TextInput, ActionRow
import asyncio




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

            # Generate more images from the selected image
            generated_images = await self.bot.get_cog('Image2Image').generate_images(selected_image_file, interaction)

            # Create a new embed with a grid of images
            embed = discord.Embed(title="Generated Images")
            for i, image_path in enumerate(generated_images):
                with open(image_path, 'rb') as f:
                    file = discord.File(f, filename=f"image{i}.png")
                    embed.set_image(url=f"attachment://image{i}.png")
                    await interaction.channel.send(embed=embed, file=file)

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
        def __init__(self, payload):
            super().__init__(title="Edit Prompt")
            self.payload = payload

            # Add a TextInput for the prompt
            self.add_item(TextInput(placeholder="Enter the new prompt", custom_id="new_prompt", value=self.payload['prompt']))

            # Add a TextInput for the negative prompt
            self.add_item(TextInput(placeholder="Enter the new negative prompt", custom_id="new_negative", value=self.payload['negative_prompt']))

            # Add a Button for submitting the changes
            self.add_item(ActionRow(Button(style=ButtonStyle.primary, label="Submit", custom_id="submit_changes")))

        async def callback(self, interaction: Interaction):
            if interaction.data["custom_id"] == "submit_changes":
                # Get the new values from the TextInput components
                new_prompt = self.get_component("new_prompt").value
                new_negative = self.get_component("new_negative").value

                # Update the payload with the new values
                self.payload['prompt'] = new_prompt
                self.payload['negative_prompt'] = new_negative

                # Regenerate the image using the updated payload
                image_data = await self.bot.get_cog('Text2Image').txt2image(self.payload)
                image_file = await self.bot.get_cog('Text2Image').pull_image(image_data)

                buttons = self.bot.get_cog('Buttons').ImageView(interaction, image_data['images'], self.payload)

                # Create the embed
                embed = await self.bot.get_cog('Commands').create_embed(interaction, self.payload['prompt'], self.payload['negative_prompt'], 
                                                                        self.payload['steps'], self.payload['seed'], self.payload['cfg_scale'])
                # Update the message with the new image
                await interaction.channel.send(embed=embed, file=image_file, view=buttons)

                # Close the modal
                await self.stop()




    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type == discord.InteractionType.component:
            button_id = interaction.data["custom_id"]
            payload = self.bot.get_cog('Buttons').payload
            self.payload = payload

            match button_id:
                case "choose_img":
                    await interaction.response.defer()
                    image_files = [os.path.join("image_cache", image_file) for image_file in os.listdir("image_cache")]
                    select_menu = self.ImageSelect(self.bot, image_files)
                    select_menu_view = self.SelectMenuView(select_menu)
                    await interaction.channel.send("Select an image to generate more from.", view=select_menu_view)

                case "upscale":
                    await interaction.response.defer()
                    image_files = [os.path.join("image_cache", image_file) for image_file in os.listdir("image_cache")]
                    select_menu = self.UpscaleSelect(self.bot, image_files)
                    select_menu_view = self.SelectMenuView(select_menu)
                    await interaction.channel.send("Select an image to upscale so you can save it.", view=select_menu_view)


                case "regenerate":
                    #await self.bot.get_cog('Buttons').regenerate(interaction)
                    await interaction.response.defer()
                    await interaction.followup.send("Regenerating...")
                    # Regenerate the image using the stored payload
                    image_data = await self.bot.get_cog('Text2Image').txt2image(self.payload)
                    image_file = await self.bot.get_cog('Text2Image').pull_image(image_data)

                    buttons = self.bot.get_cog('Buttons').ImageView(interaction, image_data['images'], self.payload)

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
                    modal = self.EditModal(self.payload)
                    await interaction.response.show_modal(modal)


                case "ai_prompt":
                    # Create modal 
                    return
                    




async def setup(bot):
    await bot.add_cog(Buttons(bot))