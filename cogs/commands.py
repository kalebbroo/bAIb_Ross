import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
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
            first_setting = self.model_setting
            settings_data = {}
            first_select_menu = await first_setting(self.bot, settings_data, start=0)
            view = discord.ui.View()
            view.add_item(first_select_menu)
            embed = discord.Embed(title=f"Setting for {first_select_menu.placeholder}", description="Choose an option.")
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
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
            titles = [file.get("title") for file in data.get("files", [])]
            filtered_titles = [title for title in titles if not title.startswith("0")]
            
            def sort_key(x):
                try:
                    return int(x.split(" ")[0].split(".")[0])
                except ValueError:
                    return float('inf')
            
            sorted_titles = sorted(filtered_titles, key=sort_key)
            return sorted_titles
                    
    async def model_setting(self, bot, settings_data, start=0):
        model_options = await self.get_model_list()
        sliced_model_options = model_options[start:start + 24]
        model_option_instances = [discord.SelectOption(label=model, value=model) for model in sliced_model_options]
        if len(model_options) > start + 24:
            model_option_instances.append(discord.SelectOption(label="Show more models...", value="Show more models..."))
        return Commands.SettingsSelect(bot, "Choose a Model", model_option_instances, self.steps_setting, settings_data, start=start)
    
    def steps_setting(self, bot, settings_data):
        step_values = ["5", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "30", "40", "50", "60", "70", "80"]
        steps = [discord.SelectOption(label=value, value=value) for value in step_values]
        return Commands.SettingsSelect(bot, "Choose Steps", steps, self.cfg_scale_setting, settings_data)

    def cfg_scale_setting(self, bot, settings_data):
        cfg_scale = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)]
        return Commands.SettingsSelect(bot, "Choose CFG Scale", cfg_scale, self.lora_setting, settings_data)

    def lora_setting(self, bot, settings_data):
        lora = [discord.SelectOption(label="Placeholder", value="Placeholder")]
        return Commands.SettingsSelect(bot, "Choose LORA", lora, self.embeddings_setting, settings_data)

    def embeddings_setting(self, bot, settings_data):
        embeddings = [discord.SelectOption(label="Placeholder", value="Placeholder")]
        return Commands.SettingsSelect(bot, "Choose Embeddings", embeddings, self.size_setting, settings_data)

    def size_setting(self, bot, settings_data):
        size_values = {
            "1:1": (1024, 1024),
            "4:3": (1024, 768),
            "3:2": (1800, 1200),
            "16:9": (1920, 1080),
            "21:9": (2560, 1080),
            "8:5": (1280, 800),
            "3:4": (768, 1024),
            "2:3": (800, 1200),
            "5:8": (720, 1280),
            "9:16": (1080, 1920),
            "9:21": (1080, 2520)
        }
        size_options = [discord.SelectOption(label=label, value=f"{width}-{height}") for label, (width, height) in size_values.items()]
        return Commands.SettingsSelect(bot, "Choose Size", size_options, None, settings_data)

                
    class SettingsSelect(discord.ui.Select):
        def __init__(self, bot, placeholder, options, next_setting=None, settings_data=None, start=0):
            super().__init__(placeholder=placeholder, options=options, row=0)
            self.bot = bot
            self.next_setting = next_setting
            self.settings_data = settings_data or {}
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
                    next_select_menu = self.next_setting(self.bot, self.settings_data)
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
                cfg_scale=settings_data.get("Choose CFG Scale"),
                lora=settings_data.get("Choose LORA"),
                embeddings=settings_data.get("Choose Embeddings")
            )
            payload.update({"ai_assistance": ai_assistance})
            await api_call.call_collect(interaction, payload)

async def setup(bot):
    await bot.add_cog(Commands(bot))
