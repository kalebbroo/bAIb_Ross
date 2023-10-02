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
        self._last_member = None
        self.eta_task = None
        self.session = aiohttp.ClientSession()

    @app_commands.command(name="dream", description="Press ENTER to Generate an image")
    @app_commands.describe(ai_assistance='Want AI to rewrite prompt?', change_settings='Do you want to edit settings?')
    async def dream(self, interaction, ai_assistance: bool, change_settings: bool):
        if change_settings:
            first_setting = self.model_setting
            settings_data = {}  # To store the selected settings
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
            
            # Filter out models that start with '0'
            filtered_titles = [title for title in titles if not title.startswith("0")]
            
            # Sort the list by the numbers
            def sort_key(x):
                try:
                    return int(x.split(" ")[0].split(".")[0])
                except ValueError:
                    return float('inf')  # Put it at the end
            
            sorted_titles = sorted(filtered_titles, key=sort_key)
            return sorted_titles
                    
    async def model_setting(self, bot, settings_data, start=0):
        model_options = await self.get_model_list()
        # Slice the model options based on the 'start' index
        sliced_model_options = model_options[start:start + 24]
        # Create discord.SelectOption instances
        model_option_instances = [discord.SelectOption(label=model, value=model) for model in sliced_model_options]
        # If there are more models to show, add a "Show more models..." option
        if len(model_options) > start + 24:
            model_option_instances.append(discord.SelectOption(label="Show more models...", value="Show more models..."))
        return Commands.SettingsSelect(bot, "Choose a Model", model_option_instances, self.steps_setting, settings_data, start=start)
    
    def steps_setting(self, bot, settings_data):
        steps = [
            discord.SelectOption(label="5", value="5"),
            discord.SelectOption(label="10", value="10"),
            discord.SelectOption(label="11", value="11"),
            discord.SelectOption(label="12", value="12"),
            discord.SelectOption(label="13", value="13"),
            discord.SelectOption(label="14", value="14"),
            discord.SelectOption(label="15", value="15"),
            discord.SelectOption(label="16", value="16"),
            discord.SelectOption(label="17", value="17"),
            discord.SelectOption(label="18", value="18"),
            discord.SelectOption(label="19", value="19"),
            discord.SelectOption(label="20", value="20"),
            discord.SelectOption(label="30", value="30"),
            discord.SelectOption(label="40", value="40"),
            discord.SelectOption(label="50", value="50"),
            discord.SelectOption(label="60", value="60"),
            discord.SelectOption(label="70", value="70"),
            discord.SelectOption(label="80", value="80"),
        ]
        return Commands.SettingsSelect(bot, "Choose Steps", steps, self.size_setting, settings_data)


    def size_setting(self, bot, settings_data):
        size_options = [
            discord.SelectOption(label="1:1", value="1:1"),
            discord.SelectOption(label="4:3", value="4:3"),
            discord.SelectOption(label="3:2", value="3:2"),
            discord.SelectOption(label="16:9", value="16:9"),
            discord.SelectOption(label="21:9", value="21:9"),
            discord.SelectOption(label="8:5", value="8:5"),
            discord.SelectOption(label="3:4", value="3:4"),
            discord.SelectOption(label="2:3", value="2:3"),
            discord.SelectOption(label="5:8", value="5:8"),
            discord.SelectOption(label="9:16", value="9:16"),
            discord.SelectOption(label="9:21", value="9:21"),
        ]
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
                # Get the next set of models and show them in a new select menu
                next_select_menu = await self.bot.get_cog("Commands").model_setting(self.bot, self.settings_data, start=self.start + 25)
                
                view = discord.ui.View()
                view.add_item(next_select_menu)
                
                embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                # Handle the selected model and proceed with the action
                self.settings_data[self.placeholder] = selected_value

                if self.next_setting:
                    next_select_menu = self.next_setting(self.bot, self.settings_data)
                    view = discord.ui.View()
                    view.add_item(next_select_menu)
                    embed = discord.Embed(title=f"Setting for {next_select_menu.placeholder}", description="Choose an option.")
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                else:
                    # All settings are selected, proceed with the action
                    user_id = interaction.user.id
                    
                    # Store the settings for this user
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

            # Retrieve the settings for this user
            user_id = interaction.user.id
            settings_data = Commands.user_settings.get(user_id, {})
            
            # Convert the "Choose Size" option to actual width and height
            size_choice = settings_data.get("Choose Size")
            size_map = {
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
                "9:21": (1080, 2520),
            }
            width, height = size_map.get(size_choice, (None, None))

            # Create the payload
            api_call = self.bot.get_cog("APICalls")
            
            # Set the session_id, prompt, negative_prompt, and other settings here
            session_id = await api_call.get_session()
            payload = api_call.create_payload(session_id, prompt=prompt, negative_prompt=negative, 
                                            model=settings_data.get("Choose a Model"), width=width,
                                            height=height, steps=settings_data.get("Choose Steps"))
            print(f"Payload being sent: {payload}")
            user_settings = {}
            # Pass the payload to the API call
            await api_call.call_collect(interaction, payload)


async def setup(bot):
    await bot.add_cog(Commands(bot))