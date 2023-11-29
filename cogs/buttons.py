import os
import discord
from discord.ext import commands
from discord import ButtonStyle, Interaction, ui
from discord.ui import Button, View, Select, Modal, TextInput
from io import BytesIO
from PIL import Image
from datetime import datetime
import base64
import asyncio
import io

class Buttons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mdl_settings = self.bot.get_cog('ModelSettings')

    """Buttons for the image grid embed"""

    class ImageButtons(View):
        def __init__(self, bot, interaction, payload, message_id=None):
            super().__init__(timeout=220)  # set the button timeout
            self.bot = bot
            self.payload = payload
            self.message_id = message_id
            self.channel_id = interaction.channel_id

            # Automatically start the countdown to disable buttons
            asyncio.create_task(self.disable_buttons())

        async def disable_buttons(self):
            await asyncio.sleep(120)
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                original_message = await channel.fetch_message(self.message_id)
                if original_message:
                    for button in self.children:
                        button.disabled = True
                    await original_message.edit(view=self)

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

                select_menu = Buttons.UpscaleSelect(self.bot, image_files, self.payload)
                view = discord.ui.View()
                view.add_item(select_menu)
                await interaction.channel.send("Select an image to upscale", view=view)

            except Exception as e:
                print(f"An exception occurred in the upscale button: {e}")

        @discord.ui.button(style=ButtonStyle.danger, label="Delete", custom_id="delete", row=1)
        async def delete(self, interaction, button):
            # Delete the message
            await interaction.response.send_message("Your shame has been deleted", ephemeral=True)
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
            image_path = self.values[0]

            # Convert the image to Base64
            with open(image_path, "rb") as f:
                image_data = f.read()
                image = base64.b64encode(image_data).decode('utf-8')

            # Create or update the payload
            payload = {
                "upscale": "true",
                "initimage": image,
                "init_image_creativity": 0,
                "model": "juggernautXL_version6Rundiffusion.safetensors",
                "width": self.payload.get('width') * 2,
                "height": self.payload.get('height') * 2,
                "images": 1,
                "steps": 60,
            }
            self.payload.update(payload)
            #print(f"Payload from upscale: {self.payload}")

            # Call the API method to upscale the image
            await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)

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
            self.payload.update({"init_image_creativity": 0.8})
            # TODO: maybe add another peram init_image_creativity

            # Generate more images from the selected image
            await self.bot.get_cog('APICalls').call_collect(interaction, self.payload)

    """Buttons for Choosing a model"""

    class ModelView(discord.ui.View):
        """The buttons for navigating between models.
        This view contains buttons for navigating to the previous model, selecting the current model,
        navigating to the next model, and generating a list of available models. It allows users to 
        interactively browse and select models and change settings before generating an image.
        """
        def __init__(self, bot, models, index, settings_data):
            super().__init__(timeout=180)
            self.bot = bot
            self.models = models
            self.index = index
            self.settings_data = settings_data

        async def send_model_embed(self, interaction):
            model = self.models[self.index]
            embed = discord.Embed(title=model.get("title", "N/A"), description=model.get("description", "N/A"), color=0x00ff00)
            
            image_file = None

            if model.get("preview_image"):
                base64_image_data = model.get("preview_image")
                if base64_image_data.startswith('data:image/jpeg;base64,'):
                    base64_image_data = base64_image_data[len('data:image/jpeg;base64,'):]

                # Decode the base64 string into bytes
                image_bytes = base64.b64decode(base64_image_data)
                # Create a discord.File object
                image_file = discord.File(io.BytesIO(image_bytes), filename="preview_image.jpeg")
                embed.set_image(url="attachment://preview_image.jpeg")  # Set the image in the embed

            # Add other details to the embed as you were doing before
            embed.add_field(name="Name", value=model.get("name", "N/A"), inline=True)
            embed.add_field(name="Standard Width", value=model.get("standard_width", "N/A"), inline=True)
            embed.add_field(name="Standard Height", value=model.get("standard_height", "N/A"), inline=True)
            embed.add_field(name="Trigger Phrase", value=model.get("trigger_phrase", "N/A"), inline=False)
            embed.add_field(name="Usage Hint", value=model.get("usage_hint", "N/A"), inline=False)
            embed.set_footer(text="Use the buttons below to navigate between models.")
            embed.timestamp = interaction.created_at

            # Send the embed
            await interaction.followup.send(embed=embed, view=self, ephemeral=True, file=image_file)

        """The buttons for navigating between model embeds."""

        # TODO: fix the code so the match case matches with the correct name of the setting
        # TODO: add the logic for LoRA and Embeddings. Maybe remove Embeddings from the code or replace it with ControlNets. Not actually sure how either of those work yet.

        @discord.ui.button(style=discord.ButtonStyle.primary, label="Back", row=1)
        async def previous_model(self, interaction, button):
            await interaction.response.defer()
            self.index = (self.index - 1) % len(self.models)
            await self.send_model_embed(interaction)

        @discord.ui.button(style=discord.ButtonStyle.success, label="Choose Model", row=1)
        async def choose_model(self, interaction, button):
            self.settings_data["Choose a Model"] = self.models[self.index]["name"]
            next_select_menu = self.bot.get_cog("ModelSettings").steps_setting(self.bot, self.settings_data, self.models)
            view = discord.ui.View()
            view.add_item(next_select_menu)
            embed = discord.Embed(
                            title="Step Selection",
                            description="""The 'Steps' setting controls the number of iterations 
                            the algorithm will perform. A higher number generally means better 
                            quality but will require more time to process.""",
                            color=discord.Color.purple()
                        )
            embed.set_image(url="https://i0.wp.com/blog.openart.ai/wp-content/uploads/2023/02/Screen-Shot-2023-02-13-at-5.11.28-PM.png?resize=1024%2C602&ssl=1")
            embed.add_field(name="Tip for Beginners", 
                            value="Start with a lower number of steps `10` to get quicker results, then increase for better quality.")
            embed.add_field(name="Note", value="Remember, these settings will affect both the processing time and the output quality.")
            embed.set_footer(text="Use the menu below to make your selection, or press the 'skip' option.")
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        @discord.ui.button(style=discord.ButtonStyle.primary, label="Next", row=1)
        async def next_model(self, interaction, button):
            await interaction.response.defer()
            self.index = (self.index + 1) % len(self.models)
            await self.send_model_embed(interaction)

        @discord.ui.button(style=discord.ButtonStyle.secondary, label="Choose From List (Know what you want?)", row=2)
        async def generate_model_list(self, interaction, button):
            model_list = await self.bot.get_cog("APICalls").get_model_list()
            options = [discord.SelectOption(label=model['title'], value=model['name']) for model in model_list[:24]]
            options.append(discord.SelectOption(label="Show more models...", value="Show more models..."))

            model_select_menu = self.mdl_settings.SettingsSelect(bot=self.bot, placeholder='Choose a Model', 
                                            options=options, next_setting=self.mdl_settings.steps_setting,
                                            settings_data=self.settings_data, model_list=model_list, start=0)
            # Create a view and add the select menu
            view = discord.ui.View()
            view.add_item(model_select_menu)

            # Create the embed
            embed = discord.Embed(title="XL models are better than 1.5 but take longer to gen", 
                                description="Read the descriptions to find the best model for you.")
            # Send the message
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
    class ConfirmationView(discord.ui.View):
        def __init__(self, bot, payload, user_id):
            super().__init__()
            self.bot = bot
            self.payload = payload
            self.user_id = user_id

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
        async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("You're not the one who initiated the command!", ephemeral=True)

            # Delete the original message
            await interaction.message.delete()

            # Send a placeholder follow-up message
            placeholder_embed = discord.Embed(description="Generating image, one moment please...")
            followup_message = await interaction.followup.send(embed=placeholder_embed, wait=True)

            # Call the API to generate the image
            api_call = self.bot.get_cog("APICalls")
            image_file = await api_call.call_collect(interaction, self.payload)

            # Once the image is ready, edit the follow-up message to display the image
            if image_file:
                generated_image_embed = discord.Embed(title="Generated Image")
                generated_image_embed.set_image(url=f"attachment://{image_file.filename}")
                await followup_message.edit(embed=generated_image_embed, attachments=[image_file])
            else:
                await followup_message.edit(content="Failed to generate image.", embed=None)


        @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            async with interaction.message.channel.typing():
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("You're not the one who initiated the command!", ephemeral=True)
                # Disable the buttons
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True

                # Update the message with the disabled buttons
                await interaction.edit_original_response(view=self)

                await interaction.response.send_message("Operation cancelled.", ephemeral=True)

                self.stop()

        @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary)
        async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("You're not the one who initiated the command!", ephemeral=True)

            ai = self.bot.get_cog("AIPromptGenerator")

            # If the prompt is not set, generate a random prompt
            if self.payload.get('prompt') is None:
                prompt, negative = await ai.gen_random_prompt()
                self.payload.update({"prompt": prompt, "negativeprompt": negative})

            # Create and send the modal
            modal = Buttons.EditPromptModal(self.bot, self, self.payload)
            await interaction.response.send_modal(modal)

        class EditPromptModal(discord.ui.Modal):
            def __init__(self, bot, view, payload):
                super().__init__(title="Edit Prompt and Negative")
                self.bot = bot
                self.view = view
                self.payload = payload

                self.prompt_input = discord.ui.TextInput(
                    label='Prompt', style=discord.TextStyle.paragraph,
                    default=self.payload.get('prompt', ''),
                    min_length=1, max_length=2000, required=True
                )
                self.negative_input = discord.ui.TextInput(
                    label='Negative Prompt', style=discord.TextStyle.paragraph,
                    default=self.payload.get('negativeprompt', ''),
                    min_length=1, max_length=2000, required=False
                )
                self.add_item(self.prompt_input)
                self.add_item(self.negative_input)

            async def on_submit(self, interaction: discord.Interaction):
                # Update the payload with the new values
                self.payload['prompt'] = self.prompt_input.value
                self.payload['negativeprompt'] = self.negative_input.value

                # Update the view with the new payload
                self.view.payload = self.payload

                # Edit the original message with the updated view
                await interaction.edit_original_response(
                    content=f"New Prompt: ```{self.payload['prompt']}```\nNew Negative: ```{self.payload['negativeprompt']}```", 
                    view=self.view)


async def setup(bot):
    await bot.add_cog(Buttons(bot))