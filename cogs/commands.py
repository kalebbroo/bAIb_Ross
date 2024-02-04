import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
from typing import List, Dict, Any
import base64
from PIL import Image
import io
import json


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
                self.models: List[Dict[str, Any]] = await api_call.get_models("model")
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
            
    @staticmethod
    async def image_to_base64(attachment):
        # Read the image bytes directly from the attachment
        image_bytes = await attachment.read()
        # Convert these bytes to a base64-encoded string
        encoded_string = base64.b64encode(image_bytes).decode("utf-8")
        return encoded_string
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        
        context = ""
        if message.reference and isinstance(message.reference, discord.MessageReference):
            # Fetch the referenced message
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if referenced_message:
                # Add context to the prompt
                context = f"Replying to a previous message: '{referenced_message.content}'\n\n"

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
                try:
                    icon_url = message.author.avatar.url
                except AttributeError:
                    icon_url = message.author.default_avatar.url

                response = await ai.gpt_phone_home(pre_prompt, context + content)
                #print(f"Response: {response}") # Debug
                generate_type = "text"  # Default value for generate_type
                if 'choices' in response and response['choices'] and 'message' in response['choices'][0] and 'content' in response['choices'][0]['message']:
                    content = response['choices'][0]['message']['content']
                    for line in content.split('\n'):
                        if line.startswith('generate_type='):
                            generate_type = line.split('=')[1].strip()
                            break
                print(f"\ngenerate_type: {generate_type}\n")  # Debug

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
                        embed = discord.Embed(
                            title="Image Generation",
                            description=f"Create an image with this? \nPrompt: ```{prompt}```\nNegative: ```{negative}```",
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text=f"Requested by {message.author.display_name}", icon_url=icon_url)
                        view = buttons.ConfirmationView(self.bot, payload, message.author.id)
                        await message.channel.send(embed=embed, view=view)
                    case "img2img":
                        if message.attachments:
                            try:
                                # Get the first attachment and convert it to base64
                                attachment = message.attachments[0]
                                buffer = io.BytesIO()
                                await attachment.save(buffer)
                                buffer.seek(0)

                                # Convert the image to base64
                                encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

                                payload = {
                                    "prompt": "Your prompt goes here",
                                    "negativeprompt": "Your negative prompt goes here"
                                }
                                # Call the img2img method with the encoded image and user
                                await self.bot.get_cog('ImageGrid').img2img(message, encoded_image, message.author, payload)

                            except Exception as e:
                                print(f"Error while processing the image: {e}")
                                await message.channel.send("An error occurred while processing the image.")
                                
                    case "txt2video":
                        # Handle text2img2video generation
                        content = response['choices'][0]['message']['content']
                        prompt, negative = ai.split_prompt(content, prompt_label="Prompt:", negative_label="Negative:")
                        session_id = await api_call.get_session()
                        payload = api_call.create_payload(session_id, prompt=prompt, negativeprompt=negative, 
                                                        video_format="gif", video_frames=25, video_fps=60, upscale=True,
                                                        video_model="OfficialStableDiffusion/svd_xt_1_1.safetensors", video_steps=20, 
                                                        video_cfg=2.5, video_min_cfg=1, video_motion_bucket="127",
                                                        width=1344, height=768, images=1, batchsize=1
                                                        )
                        buttons = self.bot.get_cog("Buttons")
                        embed = discord.Embed(
                            title="Video Generation",
                            description=f"Create a video with this? \nPrompt: ```{prompt}```\nNegative: ```{negative}```",
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text=f"Requested by {message.author.display_name}", icon_url=icon_url)
                        view = buttons.ConfirmationView(self.bot, payload, message.author.id)
                        await message.channel.send(embed=embed, view=view)
                    case "img2video":
                        # Handle img2video generation
                        if message.attachments:
                            try:
                                # Convert the attachment directly to base64
                                encoded_image = await Commands.image_to_base64(message.attachments[0])

                                session_id = await api_call.get_session()
                                prompt = "perfectly looped video"
                                negative = "NSFW"
                                payload = api_call.create_payload(session_id, prompt=prompt, negativeprompt=negative, 
                                                        init_image=encoded_image, init_image_creativity=0,
                                                        video_format="gif", video_frames=25, video_fps=60, upscale=True,
                                                        video_model="OfficialStableDiffusion/svd_xt_1_1.safetensors", video_steps=20, 
                                                        video_cfg=2.5, video_min_cfg=1, video_motion_bucket="127",
                                                        width=1344, height=768, images=1, batchsize=1
                                                        )
                                buttons = self.bot.get_cog("Buttons")
                                embed = discord.Embed(
                                    title="Image to Video Generation",
                                    description=f"""Create a video with this? Videos are made in 
                                                           16:9 Your image will be cropped to fit this\n
                                                           Do you want to continue?""",
                                    color=discord.Color.green()
                                )
                                embed.set_footer(text=f"Requested by {message.author.display_name}", icon_url=icon_url)
                                view = buttons.ConfirmationView(self.bot, payload, message.author.id)
                                await message.channel.send(embed=embed, view=view)
                            except Exception as e:
                                print(f"Error while processing the image: {e}")
                                await message.channel.send("An error occurred while processing the image.")

                    case "upscale":
                        if message.attachments:
                            try:
                                # Get the first attachment and convert it to base64
                                attachment = message.attachments[0]
                                buffer = io.BytesIO()
                                await attachment.save(buffer)
                                buffer.seek(0)

                                # Convert the image to base64
                                encoded_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

                                await self.bot.get_cog('ImageGrid').upscale(message, encoded_image, user=message.author)

                            except Exception as e:
                                print(f"Error while processing the image: {e}")
                                await message.channel.send("An error occurred while processing the image.")

                    case _:
                        # Handle any other cases or unknown types
                        print(f"Unknown generate_type: {generate_type}")
                        embed = discord.Embed(
                            title="Unknown Request",
                            description="Something went wrong. Please try again.",
                            color=discord.Color.red()
                        )
                        embed.set_footer(text=f"Requested by {message.author.display_name}", icon_url=icon_url)
                        await message.channel.send(embed=embed)



# The setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(Commands(bot))
