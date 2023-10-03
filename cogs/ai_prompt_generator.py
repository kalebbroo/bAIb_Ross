import discord
from discord.ext import commands
import openai
import os

GPT_KEY = os.getenv('GPT_KEY')

class AIPromptGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = openai
        self.openai.api_key = GPT_KEY
        self.pre_prompt = self.read_pre_prompt()
        self.openai.Model.list()

    def read_pre_prompt(self):
        with open('pre_prompt.txt', 'r', encoding='utf-8') as file:
            return file.read()

    async def rewrite_prompt(self, interaction, prompt):
        model_list = self.openai.Model.list()
        print(f"Model List: {model_list}")
        prompt = ''.join(prompt)
        response = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.pre_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        # Error handling for API response
        if 'choices' not in response or not response['choices']:
            await interaction.channel.send("Failed to rewrite the prompt.")
            return None, None
        prompt_text = response['choices'][0]['message']['content'].strip()
        prompt_parts = prompt_text.split("Negative:")

        # Extract prompt and negative, provide fallback for missing negative
        prompt = prompt_parts[0].strip()
        negative = prompt_parts[1].strip() if len(prompt_parts) > 1 else "bad quality"

        await interaction.channel.send(f"Rewritten Prompt: {prompt}")
        return prompt, negative

async def setup(bot):
    await bot.add_cog(AIPromptGenerator(bot))
