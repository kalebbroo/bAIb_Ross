import discord
from discord.ext import commands
import openai
import os
from typing import Tuple, Optional

# Get the GPT key from environment variables
GPT_KEY = os.getenv('GPT_KEY')

class AIPromptGenerator(commands.Cog):
    """A Cog for generating AI prompts."""
    def __init__(self, bot: commands.Bot):
        """Initialize the AIPromptGenerator Cog."""
        self.bot = bot
        self.openai = openai  # OpenAI API client
        self.openai.api_key = GPT_KEY  # Set the API key for OpenAI
        self.pre_prompt = self.read_pre_prompt()  # Read the pre-defined prompt instructions from file
        self.openai.Model.list()  # List available models for debugging

    def read_pre_prompt(self) -> str:
        """Read pre-defined prompts from a text file.
        Returns:
            The content of the pre_prompt.txt file as a string.
        """
        with open('pre_prompt.txt', 'r', encoding='utf-8') as file:
            return file.read()

    async def rewrite_prompt(self, interaction, prompt: str, negative: str) -> Tuple[Optional[str], Optional[str]]:
        """Rewrite the prompt using GPT-3.
        Args:
            interaction: The Discord interaction that triggered this.
            prompt: The original prompt.
            negative: The original negative prompt.
        Returns:
            A tuple containing the rewritten prompt and negative prompt.
        """
        model_list = self.openai.Model.list()  # Retrieve the list of available models (for debugging)
        print(f"Model List: {[model['id'] for model in model_list['data']]}") # Print the list of available models (for debugging)
        
        p_n = prompt + negative

        # Make an API call to rewrite the prompt
        response = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=[
                {"role": "system", "content": self.pre_prompt},  # Pre-prompt
                {"role": "user", "content": p_n},  # User's prompt and negative
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        # Error handling for the API response
        if 'choices' not in response or not response['choices']:
            await interaction.channel.send("Failed to rewrite the prompt.")
            return None, None

        prompt_text = response['choices'][0]['message']['content'].strip()  # Extract the rewritten prompt
        prompt_parts = prompt_text.split("Negative:")  # Split it into prompt and negative parts

        # Extract and return prompt and negative, with a fallback for missing negative
        prompt = prompt_parts[0].strip()
        negative = prompt_parts[1].strip() if len(prompt_parts) > 1 else "bad quality"

        return prompt, negative

async def setup(bot: commands.Bot) -> None:
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(AIPromptGenerator(bot))
