import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
from discord import ButtonStyle, Interaction, ui
from datetime import datetime
import requests
from typing import List, Dict, Any
import aiohttp
import os
import io
import base64

SWARM_URL = os.getenv('SWARM_URL')

class Commands(commands.Cog):
    user_settings = {}
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    @app_commands.command(name="dream", description="Press ENTER to Generate an image")
    @app_commands.describe(ai_assistance='Want AI to rewrite prompt?', change_settings='Do you want to edit settings?')
    async def dream(self, interaction, ai_assistance: bool, change_settings: bool):
        user_id = interaction.user.id
        Commands.user_settings[user_id] = {"ai_assistance": ai_assistance}

        if change_settings:
            await interaction.response.defer(ephemeral=True)
            settings_data: Dict[str, Any] = {}
            
            # Initialize self.models and self.index if they are not already initialized
            if not hasattr(self, 'models') or not self.models:
                self.models: List[Dict[str, Any]] = await self.get_model_list()
            self.index: int = 1  # Or whatever index you want for the initial model

            # Create an instance of ModelView
            model_view_instance = Commands.ModelView(self.bot, self.models, self.index, settings_data)
            # Send the initial embed using the send_model_embed method of ModelView instance
            await model_view_instance.send_model_embed(interaction)

        else:
            modal = self.Txt2imgModal(self.bot, interaction)
            await interaction.response.send_modal(modal)

    async def get_model_list(self):
        url = f"{SWARM_URL}/API/ListModels"
        session_id = await self.bot.get_cog("APICalls").get_session()
        params = {
            "path": "",
            "depth": 2,
            "session_id": session_id
        }
        async with self.session.post(url, json=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to get model list. HTTP Status Code: {response.status}, Response Content: {await response.text()}")
            data = await response.json()
            model_list = [
                {
                    "title": file.get("title"),
                    "name": file.get("name"),
                    "standard_width": file.get("standard_width"),
                    "standard_height": file.get("standard_height"),
                    "description": file.get("description"),
                    "preview_image": file.get("preview_image"),
                    "trigger_phrase": file.get("trigger_phrase"),
                    "usage_hint": file.get("usage_hint"),
                }
                for file in data.get("files", [])
            ]
            # Sort the model list by 'title'
            #model_list.sort(key=lambda x: (x['title'][0].isdigit(), int(''.join(filter(str.isdigit, x['title'].split()[0]))) if x['title'][0].isdigit() else x['title']))
            model_list.sort(key=lambda x: int(x['title'].split()[0].replace('.', '')))
            titles = [model['title'] for model in model_list]
            print(titles)
            
            return model_list

    class ModelView(discord.ui.View):
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


        @discord.ui.button(style=discord.ButtonStyle.primary, label="Back", row=1)
        async def previous_model(self, interaction, button):
            await interaction.response.defer()
            self.index = (self.index - 1) % len(self.models)
            await self.send_model_embed(interaction)

        @discord.ui.button(style=discord.ButtonStyle.success, label="Choose Model", row=1)
        async def choose_model(self, interaction, button):
            self.settings_data["Choose a Model"] = self.models[self.index]["name"]
            next_select_menu = self.bot.get_cog("Commands").steps_setting(self.bot, self.settings_data, self.models)
            view = discord.ui.View()
            view.add_item(next_select_menu)
            # embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
            # await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            embed = discord.Embed(
                            title="Step Selection",
                            description="""The 'Steps' setting controls the number of iterations 
                            the algorithm will perform. A higher number generally means better 
                            quality but will require more time to process.""",
                            color=discord.Color.blue()
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

        @discord.ui.button(style=discord.ButtonStyle.secondary, label="Generate Model List", row=2)
        async def generate_model_list(self, interaction, button):
            next_select_menu = await self.bot.get_cog("Commands").model_setting(self.bot, self.settings_data, start=0)
            view = discord.ui.View()
            view.add_item(next_select_menu)
            embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    async def model_setting(self, bot, interaction, settings_data, start=0):
        model_list = await self.get_model_list()
        model_view = Commands.ModelView(bot, model_list, 0, settings_data)
        first_model = model_list[0]
        return first_model, model_view
    
    def steps_setting(self, bot, settings_data, model_list):
        step_values = ["5", "8", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "30", "40", "50", "60", "70", "80"]
        steps = [discord.SelectOption(label=value, value=value) for value in step_values]
        return Commands.SettingsSelect(bot, "Choose Steps", steps, self.cfgscale_setting, settings_data, model_list)

    def cfgscale_setting(self, bot, settings_data, model_list):
        cfgscale = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)]
        return Commands.SettingsSelect(bot, "Choose CFG Scale", cfgscale, self.lora_setting, settings_data, model_list)

    def lora_setting(self, bot, settings_data, model_list):
        lora = [discord.SelectOption(label="Placeholder", value="Placeholder")]
        return Commands.SettingsSelect(bot, "Choose LORA", lora, self.embedding_setting, settings_data, model_list)

    def embedding_setting(self, bot, settings_data, model_list):
        embedding = [discord.SelectOption(label="Placeholder", value="Placeholder")]
        return Commands.SettingsSelect(bot, "Choose Embeddings", embedding, self.size_setting, settings_data, model_list)

    def scale_to_aspect_ratio(self, base_width, base_height, aspect_ratio):
        w, h = map(int, aspect_ratio.split(":"))
        new_width = base_width
        new_height = int((new_width * h) / w)
        if new_height > base_height:
            new_height = base_height
            new_width = int((new_height * w) / h)
        return new_width, new_height

    def size_setting(self, bot, settings_data, model_list):
        model_name = settings_data.get("Choose a Model")
        chosen_model = next((model for model in model_list if model["name"] == model_name), None)

        if chosen_model:
            standard_width = chosen_model.get("standard_width")
            standard_height = chosen_model.get("standard_height")
        else:
            standard_width = 1024  # Default values
            standard_height = 1024

        aspect_ratios = ["1:1", "4:3", "3:2", "16:9", "21:9", "8:5", "3:4", "2:3", "5:8", "9:16", "9:21"]
        size_values = {}
        for aspect_ratio in aspect_ratios:
            width, height = self.scale_to_aspect_ratio(standard_width, standard_height, aspect_ratio)
            size_values[aspect_ratio] = (width, height)

        size_options = [discord.SelectOption(label=label, value=f"{width}-{height}") for label, (width, height) in size_values.items()]
        return Commands.SettingsSelect(bot, "Choose Size", size_options, None, settings_data)

                
    class SettingsSelect(discord.ui.Select):
        def __init__(self, bot, placeholder, options, next_setting=None, settings_data=None, model_list=None, start=0):
            super().__init__(placeholder=placeholder, options=options, row=0)
            self.bot = bot
            self.next_setting = next_setting
            self.settings_data = settings_data or {}
            self.model_list = model_list
            self.start = start

        async def callback(self, interaction: discord.Interaction):
            selected_value = self.values[0]
            
            # If the selected value is for showing more models, this block will execute
            if selected_value == "Show more models...":
                next_select_menu = await self.bot.get_cog("Commands").model_setting(self.bot, self.settings_data, start=self.start + 25)
                view = discord.ui.View()
                view.add_item(next_select_menu)
                #embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                # Update settings_data with the current selected value
                self.settings_data[self.placeholder] = selected_value
                
                # Initialize the embed for the current setting
                #embed = discord.Embed(title=f"Setting for {self.placeholder}", description="Choose an option.")
                match self.placeholder:
                    case "Choose Steps":
                        embed = discord.Embed(
                            title="CFG Scale Setting",
                            description="""How strongly to scale prompt input.
                                        Higher CFG scales tend to produce more contrast, and lower CFG scales produce less contrast.
                                        Too-high values can cause corrupted/burnt images, too-low can cause nonsensical images.
                                        7 is a good baseline. Normal usages vary between 5 and 9.""",
                            color=discord.Color.green()
                        )
                        embed.add_field(name="Tip for Beginners", 
                                        value="Try different scales to explore various artistic effects.")

                    case "Choose CFG Scale":
                        embed = discord.Embed(
                            title="LORA Configuration",
                            description="""LORA (Level of Realistic Artistry) is a setting that 
                            influences how realistic the generated image will be.""",
                            color=discord.Color.red()
                        )
                        embed.add_field(name="Tip for Beginners", 
                                        value="If you're unsure, start with the default LORA setting.")

                    case "Choose LORA":
                        embed = discord.Embed(
                            title="Embedding Options",
                            description="""Embeddings are pre-trained data structures that the 
                            algorithm uses to understand the content. Different embeddings can 
                            produce different styles.""",
                            color=discord.Color.purple()
                        )
                        embed.add_field(name="Tip for Beginners", 
                                        value="Stick to the default embeddings when you're just starting out.")

                    case "Choose Embeddings":
                        embed = discord.Embed(
                            title="Image Size Selection",
                            description="""This setting allows you to choose the dimensions of 
                            the output image. Different sizes will have an impact on the processing 
                            time and quality.""",
                            color=discord.Color.orange()
                        )
                        embed.add_field(name="Tip for Beginners", 
                                        value="Start with smaller sizes for faster results.")

                    # Prepare for the next setting
                if self.next_setting:
                    next_select_menu = self.next_setting(self.bot, self.settings_data, self.model_list)
                    view = discord.ui.View()
                    view.add_item(next_select_menu)
                else:
                    # If there's no next setting send modal
                    user_id = interaction.user.id
                    Commands.user_settings[user_id] = self.settings_data
                    modal = Commands.Txt2imgModal(self.bot, interaction)
                    await interaction.response.send_modal(modal)
                    return
                
                # Common fields that appear in all embeds
                embed.add_field(name="Note", value="Remember, these settings will affect both the processing time and the output quality.")
                embed.set_footer(text="Use the menu below to make your selection, or press the 'skip' option.")
                
                # Send the embed
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    class Txt2imgModal(Modal):
        def __init__(self, bot, interaction):
            super().__init__(title="Enter Prompt")
            self.bot = bot
            self.prompt = TextInput(label='Enter your prompt', style=discord.TextStyle.paragraph,
                                    default=f'portrait of a frog wearing a crown, ((sitting on a lily pad)), pond, castle background, digital painting,'
                                            f'hyperrealistic, deviantart, 8k, cinematic lighting, dramatic, low angle shot',
                                    min_length=1, max_length=2000, required=True)
            self.negative = TextInput(label='Enter your negative', style=discord.TextStyle.paragraph,
                                   default=f'low resolution, bad quality, blurry, simple background, white background, plain background, normal quality,'
                                           f'6 fingers, extra fingers, broken fingers, worst quality, 2D, pop-art, pixabay, normal focus, flat lighting, boring',
                                           min_length=1, max_length=2000, required=True)
            self.add_item(self.prompt)
            self.add_item(self.negative)

        async def on_submit(self, interaction):
            await interaction.response.defer()
            prompt = self.prompt.value
            negative = self.negative.value
            user_id = interaction.user.id
            settings_data = Commands.user_settings.get(user_id, {})
            api_call = self.bot.get_cog("APICalls")
            session_id = await api_call.get_session()

            # Create the payload
            payload = api_call.create_payload(
                    session_id, 
                    prompt=prompt, 
                    negative_prompt=negative,
                )

            # Convert the "Choose Size" option to actual width and height
            size_choice = settings_data.get("Choose Size")
            if size_choice:
                width, height = map(int, size_choice.split('-'))
                # Update the payload with all user defined settings
                payload.update({
                    "width": width,
                    "height": height,
                    "cfgscale": settings_data.get("Choose CFG Scale"),
                    "steps": settings_data.get("Choose Steps"),
                    "lora": None,  # settings_data.get("Choose LORA"),
                    "embedding": None,  # settings_data.get("Choose Embedding"),
                    "model": settings_data.get("Choose a Model")
                })

            # If AI assistance is enabled, rewrite the prompt and negative
            ai_assistance = settings_data.get("ai_assistance", False)
            if ai_assistance:
                print("AI assistance is enabled")
                ai = self.bot.get_cog("AIPromptGenerator")
                prompt, negative = await ai.rewrite_prompt(interaction, prompt, negative)
                # Create the payload
                payload['prompt'] = prompt
                payload['negative_prompt'] = negative

                await interaction.followup.send(f"Bots are speaking with bots. Please wait.", ephemeral=True)

            # API call to generate image
            await api_call.call_collect(interaction, payload)

async def setup(bot):
    await bot.add_cog(Commands(bot))
