import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
import openai
from config import GPT_KEY
from payload import Payload

class AIPromptGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = openai
        self.openai.api_key = GPT_KEY
        self.openai.Model.list()


    @app_commands.command(name="ai_prompt_generator", description="Utilizes AI to generate a better prompt")
    async def ai_prompt_generator(self, interaction):
        # Get the payload
        payload_instance = Payload(self.bot)
        payload = await payload_instance.create_payload(prompt="Your prompt", negative_prompt="Your negative prompt")


        # Create the modal and open it
        modal = self.bot.get_cog('AIPromptGenerator').GPTModal(self.bot, payload)
        await interaction.response.send_modal(modal)


    async def rewrite_prompt(self, interaction, original_prompt: str):
        with open('pre_prompt.txt', 'r', encoding='utf-8') as file:
            pre_prompt = file.read()


        response = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": pre_prompt},
                {"role": "user", "content": original_prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )

        rewritten_prompt = response['choices'][0]['message']['content'].strip()
        await interaction.channel.send(f"Rewritten Prompt: {rewritten_prompt}")
        return rewritten_prompt




    class GPTModal(Modal):
        def __init__(self, bot, payload):
            super().__init__(title="Have AI Generate a Better Prompt")
            self.bot = bot
            self.payload = payload


            # Add a TextInput for the prompt
            self.prompt = TextInput(label='Format must be [Prompt: Negative:]',
                                    style=discord.TextStyle.paragraph,
                                    default=f'[Main Focus]: a girl with pink hair [Background / Atmosphere]: foggy woods dusk [Style / Quality]: highest quality, 8k, DLSR photo, anime style [Negative]:missing limbs, nsfw, bad quality',
                                    min_length=1,
                                    max_length=2000,
                                    required=True)
            self.model = TextInput(label='Choose 1 Model, delete the rest',
                                            style=discord.TextStyle.paragraph,
                                            #placeholder=f'{model}',
                                            default='formatted_list',
                                            min_length=1,
                                            max_length=2000,
                                            required=False)
            self.settings = TextInput(label='Enter values to change settings',
                                            style=discord.TextStyle.paragraph,
                                            placeholder='Enter your settings here',
                                            default="Steps: 10, Seed: -1, CFG Scale: 0.9, Width: 512, Height: 512",
                                            min_length=1,
                                            max_length=2000,
                                            required=False)
            self.styles = TextInput(label='Choose Styles and VAE',
                                            style=discord.TextStyle.paragraph,
                                            placeholder='Choose Styles LORA VAE',
                                            default="pre filled out text",
                                            min_length=1,
                                            max_length=2000,
                                            required=False)
            # Add the TextInput components to the modal
            self.add_item(self.prompt)
            self.add_item(self.styles)
            self.add_item(self.model)
            self.add_item(self.settings)

        async def on_submit(self, interaction):
            await interaction.response.defer()

            await interaction.channel.send("Generating images with new settings...")

            # Get the new values from the TextInput components
            new_prompt = self.prompt.value
            #new_negative = self.negative_prompt.value

            # Update the payload with the new values
            self.payload['prompt'] = new_prompt
            #self.payload['negative_prompt'] = new_negative

            # Send the new prompt and negative prompt to the Chat GPT API
            rewritten_prompt = await self.bot.get_cog('AIPromptGenerator').rewrite_prompt(interaction, new_prompt)

            # Update the payload with the better prompt
            self.payload['prompt'] = rewritten_prompt
            self.payload['batch_size'] = 4

            # Regenerate the image using the updated payload
            #print (self.payload)
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

async def setup(bot):
    await bot.add_cog(AIPromptGenerator(bot))

    #TODO: fix payload getting sent to the API from Modal submit. fix response from AI
