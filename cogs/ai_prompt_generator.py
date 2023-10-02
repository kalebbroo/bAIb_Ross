import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
import openai
from dotenv import load_dotenv
import os

load_dotenv()
GPT_KEY = os.getenv('GPT_KEY')

class AIPromptGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = openai
        self.openai.api_key = GPT_KEY
        self.openai.Model.list()


    @app_commands.command(name="ai_prompt_generator", description="Utilizes AI to generate a better prompt")
    async def ai_prompt_generator(self, interaction):
        # Get the payload
        # payload_instance = Payload(self.bot)
        # payload = await payload_instance.create_payload(prompt="Your prompt", negative_prompt="Your negative prompt")


        # Create the modal and open it
        #model_list = self.bot.model_list
        #print(f'model list: {model_list}')
        modal = self.bot.get_cog('AIPromptGenerator').GPTModal(self.bot)
        await interaction.response.send_modal(modal)


    async def rewrite_prompt(self, interaction, prompt):
        prompt = ''.join(prompt)
        with open('pre_prompt.txt', 'r', encoding='utf-8') as file:
            pre_prompt = file.read()


        response = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": pre_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )

        prompt = response['choices'][0]['message']['content'].strip()
        prompt_parts = prompt.split("Negative:")
        prompt = prompt_parts[0].strip()
        negative = prompt_parts[1].strip()
        await interaction.channel.send(f"Rewritten Prompt: {prompt}")
        return prompt, negative




    class GPTModal(Modal):
        def __init__(self, bot):
            super().__init__(title="Have AI Generate a Better Prompt")
            self.bot = bot

            model_list = self.bot.model_list
            # Add a TextInput for the prompt
            self.prompt = TextInput(label='Format must be [Prompt: Negative:]',
                                    style=discord.TextStyle.paragraph,
                                    default=f'[Main Focus]: a girl with pink hair [Background / Atmosphere]: foggy woods dusk [Style / Quality]: highest quality, 8k, DLSR photo, anime style [Negative]:missing limbs, nsfw, bad quality',
                                    min_length=1,
                                    max_length=2000,
                                    required=True)
            self.model = TextInput(label='Choose 1 Model. Format must be 1. model_name',
                                            style=discord.TextStyle.paragraph,
                                            #placeholder=f'{model_list}',
                                            default=(model_list),
                                            min_length=1,
                                            max_length=2000,
                                            required=False)
            self.settings = TextInput(label='Enter values to change settings',
                                            style=discord.TextStyle.paragraph,
                                            placeholder='Change your settings here',
                                            default="[Steps]: 10, [Seed]: -1, [CFG Scale]: 7.0, [Width]: 512, [Height]: 512",
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

            await interaction.channel.send("Bots are currently speaking with other bots to generate your prompt... Please wait...")

            # Get the new values from the TextInput components
            prompt = self.prompt.value
            styles = self.styles.value
            model = self.model.value
            settings = self.settings.value
            #new_negative = self.negative_prompt.value

            # Update the payload with the new values
            #self.payload['prompt'] = new_prompt
            #self.payload['negative_prompt'] = new_negative

            prompt, model, steps, seed, cfg_scale, batch_size = await self.bot.get_cog('ParseModal').parse_modal(interaction, prompt, styles, model, settings)

            # Send the new prompt and negative prompt to the Chat GPT API
            prompt, negative = await self.bot.get_cog('AIPromptGenerator').rewrite_prompt(interaction, prompt)

            payload = {'prompt': prompt, 'negative_prompt': negative, 'model': model, 'steps': steps, 
                       'seed': seed, 'cfg_scale': cfg_scale, 'batch_size': batch_size}
            interaction.client.payloads[str(interaction.user.id)] = payload
            # Update the payload with the better prompt
            #self.payload['prompt'] = rewritten_prompt
            #self.payload['batch_size'] = 4

            # Regenerate the image using the updated payload
            #print (f"payload after AI: {payload}")
            response_data, payload = await self.bot.get_cog('Text2Image').txt2image(payload)
            image_file = await self.bot.get_cog('Text2Image').pull_image(response_data, interaction)
            print (f"payload after txt2img: {payload}")

            buttons = self.bot.get_cog('Buttons').ImageView(interaction, response_data['images'], payload)

            # Create the embed
            embed = await self.bot.get_cog('Commands').create_embed(interaction, payload['prompt'], payload['negative_prompt'], 
                                                                    payload['steps'], payload['seed'], payload['cfg_scale'])
            # Update the message with the new image
            await interaction.channel.send(embed=embed, file=image_file, view=buttons)

            # Close the modal
            self.stop()

async def setup(bot):
    await bot.add_cog(AIPromptGenerator(bot))
