import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
from typing import List, Dict, Any
import base64
import re


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
            
    async def image_to_base64(image_path):
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if self.bot.user.mentioned_in(message):
            content = message.content.replace(f'<@!{self.bot.user.id}>', '').strip()
            api_call = self.bot.get_cog("APICalls")
            ai = self.bot.get_cog("AIPromptGenerator")

            async with message.channel.typing():
                try:
                    with open('baib_ross.txt', 'r', encoding='utf-8') as file:
                        pre_prompt = file.read()
                except FileNotFoundError:
                    await message.channel.send("Sorry, there was an error processing your request.")
                    return

                response = await ai.gpt_phone_home(pre_prompt, content)
                print(f"Response: {response}") # Debug
                if 'choices' in response and response['choices'] and 'message' in response['choices'][0] and 'content' in response['choices'][0]['message']:
                    content = response['choices'][0]['message']['content']
                    for line in content.split('\n'):
                        if line.startswith('generate_type='):
                            generate_type = line.split('=')[1].strip()
                            break

                match generate_type:
                    case "text":
                        # Handle text generation
                        await message.channel.send(content)
                    case "txt2img":
                        # Handle image generation
                        content = response['choices'][0]['message']['content']
                        prompt, negative = ai.split_prompt(content, prompt_label="Prompt:", negative_label="Negative:")
                        session_id = await api_call.get_session()
                        payload = api_call.create_payload(session_id, prompt=prompt, negativeprompt=negative)
                        buttons = self.bot.get_cog("Buttons")
                        view = buttons.ConfirmationView(self.bot, payload, message.author.id)
                        await message.channel.send(f"Create an image with this? ```{prompt}```\n```{negative}``` Continue?", view=view)
                    case "img2img":
                        # Handle img2img generation
                        if message.attachments:
                            image_path = await message.attachments[0].save(fp="temp_image.png")  # Save the image temporarily
                            encoded_image = await Commands.image_to_base64(image_path)
                            payload = api_call.create_payload(session_id, initimage=encoded_image, 
                                                              init_image_creativity=0.3,)
                    case "txt2video":
                        # Handle video generation
                        content = response['choices'][0]['message']['content']
                        prompt, negative = ai.split_prompt(content, prompt_label="Prompt:", negative_label="Negative:")
                        session_id = await api_call.get_session()
                        payload = api_call.create_payload(session_id, prompt=prompt, negativeprompt=negative, 
                                                        video_format="gif", video_frames=15, video_fps=6, upscale=True,
                                                        video_model="OfficialStableDiffusion/svd_xt.safetensors", video_steps=5, 
                                                        video_cfg=2.5, video_min_cfg=1, video_motion_bucket="127",
                                                        width=1344, height=768,
                                                        )
                        buttons = self.bot.get_cog("Buttons")
                        view = buttons.ConfirmationView(self.bot, payload, message.author.id)
                        await message.channel.send(f"Create a video with this? ```{prompt}```\n```{negative}``` Continue?", view=view)
                    case "img2video":
                        # Handle img2video generation
                        if message.attachments:
                            image_path = await message.attachments[0].save(fp="temp_image.png")
                            encoded_image = await Commands.image_to_base64(image_path)
                            payload = api_call.create_payload(session_id, initimage=encoded_image, upscale=True,
                                                            prompt=prompt, negativeprompt=negative, 
                                                            video_format="gif", video_frames=25, video_fps=6, 
                                                            video_model="OfficialStableDiffusion/svd_xt.safetensors", video_steps=15, 
                                                            video_cfg=2.5, video_min_cfg=1, video_motion_bucket="127"
                                                            )
                    case "upscale":
                        # Handle upscale
                        if message.attachments:
                            image_path = await message.attachments[0].save(fp="temp_image.png")
                            encoded_image = await Commands.image_to_base64(image_path)
                            payload = api_call.create_payload(session_id, initimage=encoded_image, init_image_creativity=0.3,
                                                            width=payload["width"] * 2, height=payload["height"] * 2, 
                                                            upscale=True, images=1, steps=60, cfgscale=10, )
                    case _:
                        # Handle any other cases or unknown types
                        print(f"Unknown generate_type: {generate_type}")
                        await message.channel.send("Something went wrong. Please try again.")



# The setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(Commands(bot))
