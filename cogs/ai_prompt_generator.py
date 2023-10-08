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
        print(f"\nModel List: {[model['id'] for model in model_list['data']]}\n\n") # Print the list of available models (for debugging)
        
        # Add 'Prompt:' and 'Negative:' to user's original prompt and negative
        user_prompt = f"Prompt: {prompt}"
        user_negative = f"Negative: {negative}"
        
        # Combine the modified prompt and negative into one string
        p_n = f"{user_prompt}\n\n{user_negative}"
        print(f"Debug: p_n = {p_n}\n\n")

        # Make an API call to rewrite the prompt
        response = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0301",
            messages=[
                {"role": "system", "content": self.pre_prompt},  # Pre-prompt
                {"role": "user", "content": p_n},  # User's prompt and negative
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        # After getting the API response
        prompt_text = response['choices'][0]['message']['content'].strip()
        print(f"Debug: prompt_text = {prompt_text}\n\n")
        
        # Split the text into 'prompt' and 'negative'
        prompt_parts = prompt_text.split("This is the rewritten Negative:")
        
        if len(prompt_parts) == 2:
            # Extract the two parts and remove the headers
            prompt, negative = map(str.strip, prompt_parts)
            prompt = prompt.replace("This is the rewritten Prompt:", "").strip()
        else:
            # Handle cases where splitting didn't work as expected
            print(f"Debug: Splitting failed, prompt_parts = {prompt_parts}\n")
            prompt, negative = None, None

        print(f"Debug: returned prompt = {prompt}\n\n")
        print(f"Debug: returned negative = {negative}\n\n")
        return prompt, negative

async def setup(bot: commands.Bot) -> None:
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(AIPromptGenerator(bot))
