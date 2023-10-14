import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
from typing import List, Dict, Any


class Commands(commands.Cog):
    """Main commands for the bot."""
    
    # Store settings in a class-level dictionary
    user_settings: Dict[str, Dict[str, Any]] = {} 

    def __init__(self, bot: commands.Bot):
        """Initialize the Commands cog."""
        self.bot = bot

    @app_commands.command(name="dream", description="Press ENTER to Generate an image")
    @app_commands.describe(ai_assistance='Want AI to rewrite prompt?', change_settings='Do you want to edit settings?')
    async def dream(self, interaction: discord.Interaction, ai_assistance: bool, change_settings: bool):
        """Handle the /dream command.
        Args:
            interaction: The Discord interaction object.
            ai_assistance: Whether to use AI for rewriting the prompt.
            change_settings: Whether the user wants to change settings.
        """
        user_id = str(interaction.user.id)  # Convert user ID to string

        # Initialize user settings with user_id as the key
        if user_id not in Commands.user_settings:
            Commands.user_settings[user_id] = {
                "ai_assistance": ai_assistance,
                "change_settings": change_settings,
                "payload": {},
                "settings_data": {}
            }
        Commands.user_settings[user_id]["ai_assistance"] = ai_assistance
        Commands.user_settings[user_id]["change_settings"] = change_settings
        print(f"Ai Assistance right after cmd: {ai_assistance}")

        if change_settings:
            await interaction.response.defer(ephemeral=True)
            api_call = self.bot.get_cog("APICalls")
            # Initialize self.models and self.index if they are not already initialized
            if not hasattr(self, 'models') or not self.models:
                self.models: List[Dict[str, Any]] = await api_call.get_model_list()
            self.index: int = 1  # Or whatever index you want for the initial model
            
            settings_data = Commands.user_settings[user_id]["settings_data"]
            buttons = self.bot.get_cog("Buttons")
            # Create an instance of ModelView
            model_view = buttons.ModelView(self.bot, self.models, self.index, settings_data)
            # Send the initial embed using the send_model_embed method of ModelView instance
            await model_view.send_model_embed(interaction)

        else:
            # Display the modal for text to image conversion
            modal = Commands.Txt2imgModal(self.bot, interaction, self.bot.ran_prompt, self.bot.ran_negative)
            await interaction.response.send_modal(modal)
            ai = self.bot.get_cog("AIPromptGenerator")
            self.bot.ran_prompt, self.bot.ran_negative = await ai.gen_random_prompt()

    class Txt2imgModal(Modal):
        def __init__(self, bot, interaction, ran_prompt, ran_negative):
            super().__init__(title="Enter Prompt")
            self.bot = bot
            self.prompt = TextInput(label='Enter your prompt', style=discord.TextStyle.paragraph,
                                    default=ran_prompt,
                                    min_length=1, max_length=2000, required=True)
            self.negative = TextInput(label='Enter your negative', style=discord.TextStyle.paragraph,
                                    default=ran_negative,
                                    min_length=1, max_length=2000, required=True)
            
            self.add_item(self.prompt)
            self.add_item(self.negative)

        async def on_submit(self, interaction):
            await interaction.response.defer()
            prompt = self.prompt.value
            negative = self.negative.value
            user_id = str(interaction.user.id)
            settings_data = Commands.user_settings.get(user_id, {}).get("settings_data", {})

            print(f"Debug: settings_data is {settings_data}")  # Debugging line

            api_call = self.bot.get_cog("APICalls")
            session_id = await api_call.get_session()

            # Create the payload
            payload = api_call.create_payload(
                    session_id,
                    prompt=prompt, 
                    negativeprompt=negative,
                )

            # Convert the "Choose Size" option to actual width and height
            size_choice = settings_data.get("Choose Size")
            if size_choice:
                width, height = map(int, size_choice.split('-'))
                payload.update({
                    "width": width,
                    "height": height,
                    "cfgscale": settings_data.get("Choose CFG Scale"),
                    "steps": settings_data.get("Choose Steps"),
                    "lora": None,  # settings_data.get("Choose LORA"),
                    "embedding": None,  # settings_data.get("Choose Embedding"),
                    "model": settings_data.get("Choose a Model")
                })

            ai_assistance = Commands.user_settings.get(user_id, {}).get("ai_assistance", False)

            print(f"Debug: ai_assistance is {ai_assistance}")  # Debugging line

            if ai_assistance:  # Checking for True explicitly
                print("AI assistance is enabled")  # Debugging line
                ai = self.bot.get_cog("AIPromptGenerator")
                prompt, negative = await ai.rewrite_prompt(prompt, negative)
                payload['prompt'] = prompt
                payload['negativeprompt'] = negative

                await interaction.followup.send(f"Bots are speaking with bots. Please wait.", ephemeral=True)

            # API call to generate image
            await api_call.call_collect(interaction, payload)


# The setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(Commands(bot))
