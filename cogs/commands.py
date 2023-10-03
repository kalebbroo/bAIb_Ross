import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
from discord import ButtonStyle, Interaction, ui
import requests
from typing import List
import aiohttp
import os

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
            settings_data = {}
            first_model, model_view = await self.model_setting(self.bot, interaction, settings_data, start=0)
            embed = discord.Embed(title=f"Setting for {first_model['title']}", description="Choose an option.")
            await interaction.response.send_message(embed=embed, view=model_view, ephemeral=True)

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
            #print(model_list)
            return model_list
                    
    class ModelView(discord.ui.View):
        def __init__(self, bot, models, index, settings_data):
            super().__init__(timeout=180)
            self.bot = bot
            self.models = models
            self.index = index
            self.settings_data = settings_data
            
            self.add_item(Button(style=ButtonStyle.primary, label="Next", custom_id="next_model"))
            self.add_item(Button(style=ButtonStyle.primary, label="Back", custom_id="previous_model"))
            self.add_item(Button(style=ButtonStyle.success, label="Choose Model", custom_id="choose_model"))
            self.add_item(Button(style=ButtonStyle.secondary, label="Choose from List", custom_id="choose_from_list"))

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            button_id = interaction.data["custom_id"]

            match button_id:
                case "next_model":
                    await interaction.response.defer()
                    self.index = (self.index + 1) % len(self.models)
                    await self.send_model_embed(interaction)
                case "previous_model":
                    await interaction.response.defer()
                    self.index = (self.index - 1) % len(self.models)
                    await self.send_model_embed(interaction)
                case "choose_model":
                    self.settings_data["Choose a Model"] = self.models[self.index]["name"]
                    next_select_menu = await self.bot.get_cog("Commands").steps_setting(self.bot, self.settings_data, self.models)
                    view = discord.ui.View()
                    view.add_item(next_select_menu)
                    embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                    return
                case "choose_from_list":
                    next_select_menu = await self.bot.get_cog("Commands").model_setting(self.bot, self.settings_data, start=0)
                    view = discord.ui.View()
                    view.add_item(next_select_menu)
                    embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                    return
            await self.send_model_embed(interaction)

    async def send_model_embed(self, interaction):
        model = self.models[self.index]
        embed = discord.Embed(title=model["title"], description=model["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    async def model_setting(self, bot, interaction, settings_data, start=0):
        model_list = await self.get_model_list()
        model_view = Commands.ModelView(bot, model_list, 0, settings_data)
        first_model = model_list[0]
        return first_model, model_view

    
    def steps_setting(self, bot, settings_data, model_list):
        step_values = ["5", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "30", "40", "50", "60", "70", "80"]
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
            if selected_value == "Show more models...":
                next_select_menu = await self.bot.get_cog("Commands").model_setting(self.bot, self.settings_data, start=self.start + 25)
                view = discord.ui.View()
                view.add_item(next_select_menu)
                embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                self.settings_data[self.placeholder] = selected_value
                if self.next_setting:
                    next_select_menu = self.next_setting(self.bot, self.settings_data, self.model_list)
                    view = discord.ui.View()
                    view.add_item(next_select_menu)
                    embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                else:
                    user_id = interaction.user.id
                    Commands.user_settings[user_id] = self.settings_data
                    modal = Commands.Txt2imgModal(self.bot, interaction)
                    await interaction.response.send_modal(modal)

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
            prompt = self.prompt.value
            await interaction.response.send_message(f"Creating image from prompt: {prompt}", ephemeral=True)
            negative = self.negative.value
            user_id = interaction.user.id
            settings_data = Commands.user_settings.get(user_id, {})
            ai_assistance = settings_data.get("ai_assistance", False)

            # Convert the "Choose Size" option to actual width and height
            size_choice = settings_data.get("Choose Size")
            if size_choice:
                width, height = map(int, size_choice.split('-'))
            else:
                width, height = None, None

            # Create the payload
            api_call = self.bot.get_cog("APICalls")
            session_id = await api_call.get_session()
            payload = api_call.create_payload(
                session_id, 
                prompt=prompt, 
                negative_prompt=negative,
                model=settings_data.get("Choose a Model"),
                width=width,
                height=height,
                steps=settings_data.get("Choose Steps"),
                cfgscale=settings_data.get("Choose CFG Scale"),
                lora=settings_data.get("Choose LORA"),
                embedding=settings_data.get("Choose Embedding")
            )
            payload.update({"ai_assistance": ai_assistance})
            await api_call.call_collect(interaction, payload)

async def setup(bot):
    await bot.add_cog(Commands(bot))
