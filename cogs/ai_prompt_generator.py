import discord
from discord.ext import commands
import openai
import os
from typing import Tuple, Optional, Any, Dict

# Get the GPT key from environment variables
GPT_KEY = os.getenv('GPT_KEY')

class AIPromptGenerator(commands.Cog):
    """A Cog for generating AI prompts."""
    def __init__(self, bot: commands.Bot):
        """Initialize the AIPromptGenerator Cog."""
        self.bot = bot
        self.openai = openai  # OpenAI API client
        self.openai.api_key = GPT_KEY  # Set the API key for OpenAI
        # Read the pre-defined instructions from text files
        self.pre_prompt = self.read_instructions('pre_prompt.txt')
        self.random_prompt = self.read_instructions('random_prompt.txt')
        self.openai.Model.list()  # List available models for debugging

    def read_instructions(self, filename: str) -> str:
        """Read pre-defined instructions from a text file.
        Args:
            filename: The name of the file to read.
        Returns:
            The content of the file as a string.
        """
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()

    async def gpt_phone_home(self, instruction: str, p_n: str) -> Dict[str, Any]:
        """Make the API call using GPT-3."""
        #model_list = self.openai.Model.list()  # Retrieve the list of available models (for debugging)
        #print(f"\nModel List: {[model['id'] for model in model_list['data']]}\n\n") # Print the list of available models (for debugging)
        # Make an API call to rewrite the prompt
        response = self.openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0301",
            messages=[
                {"role": "system", "content": instruction},  # System's instructions
                {"role": "user", "content": p_n},  # User's prompt and negative
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        return response

    async def rewrite_prompt(self, prompt: str, negative: str) -> Tuple[Optional[str], Optional[str]]:
        """Rewrite the prompt using GPT-3.
        Args:
            interaction: The Discord interaction that triggered this.
            prompt: The original prompt.
            negative: The original negative prompt.
        Returns:
            A tuple containing the rewritten prompt and negative prompt.
        """
        # Add 'Prompt:' and 'Negative:' to user's original prompt and negative
        user_prompt = f"Prompt: {prompt}"
        user_negative = f"Negative: {negative}"
        
        # Combine the modified prompt and negative into one string
        p_n = f"{user_prompt}\n\n{user_negative}"
        #print(f"Debug: p_n = {p_n}\n\n")

        # Make an API call to rewrite the prompt
        response = await self.gpt_phone_home(self.pre_prompt, p_n)

        # After getting the API response
        prompt_text = response['choices'][0]['message']['content'].strip()
        #print(f"Debug: prompt_text = {prompt_text}\n\n")

        # Use the new split_prompt method to split the text into 'prompt' and 'negative'
        prompt, negative = self.split_prompt(prompt_text, "This is the rewritten Prompt:", "This is the rewritten Negative:")

        #print(f"Debug: returned prompt = {prompt}\n\n")
        #print(f"Debug: returned negative = {negative}\n\n")
        return prompt, negative        
    
    async def gen_random_prompt(self):
        """Generate a random prompt using GPT-3.
        Returns:
            A tuple containing the generated prompt and negative prompt.
        """
        p_n = "Create a random prompt and negative with the subject being a random movie or scenery."
        response = await self.gpt_phone_home(self.random_prompt, p_n)

        # After getting the API response
        prompt_text = response['choices'][0]['message']['content'].strip()
        #print(f"Debug: prompt_text = {prompt_text}\n\n")

        # Split the text into 'prompt' and 'negative'
        prompt, negative = self.split_prompt(prompt_text, "This is the random Prompt:", "This is the random Negative:")

        #print(f"Debug: returned prompt = {prompt}\n\n")
        #print(f"Debug: returned negative = {negative}\n\n")
        return prompt, negative
    
    def split_prompt(self, prompt_text: str, prompt_label: str, negative_label: str) -> Tuple[Optional[str], Optional[str]]:
        """Split the returned prompt text into 'prompt' and 'negative'.
        Args:
            prompt_text: The combined prompt and negative text returned by GPT-3.
            prompt_label: The label used to identify the prompt in the text.
            negative_label: The label used to identify the negative in the text.
        Returns:
            A tuple containing the split 'prompt' and 'negative'.
        """
        # Split the text using the negative label
        prompt_parts = prompt_text.split(negative_label)
        
        if len(prompt_parts) == 2:
            # Extract the two parts and strip leading/trailing whitespace
            prompt, negative = map(str.strip, prompt_parts)
            # Remove the prompt label from the prompt part
            prompt = prompt.replace(prompt_label, "").strip()
        else:
            # Handle cases where splitting didn't work as expected
            print(f"Debug: Splitting failed, prompt_parts = {prompt_parts}\n")
            prompt, negative = None, None

        return prompt, negative

async def setup(bot: commands.Bot) -> None:
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(AIPromptGenerator(bot))
