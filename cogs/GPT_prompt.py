import discord
from discord.ext import commands
from openai import OpenAI, GPT3Completion
from copnfig import GPT_KEY

class AIPromptGenerator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai = OpenAI(f"{GPT_KEY}")

    class GPT3Rewrite:
        def __init__(self, prompt: str, original_prompt: str):
            self.prompt = prompt
            self.original_prompt = original_prompt

    class AIModal(discord.ui.View):
        def __init__(self, image: bytes, prompt: str):
            super().__init__()
            

    @commands.command(
        name="rewrite_prompt",
        description="Rewrite a prompt for generating an image with Stable Diffusion",
    )
    async def rewrite_prompt(self, ctx, *, original_prompt: str):
        pre_prompt = "You are an expert prompt creator for making prompts for Stable Diffusion to create amazing images. Rewrite this prompt to make the best quality image possible for what I'm looking for. Make sure to create a detailed and long prompt so it will correctly generate the image I want."
        full_prompt = f"{pre_prompt}\n\nOriginal Prompt: {original_prompt}\n\nRewritten Prompt:"

        response = self.openai.complete(
            model="text-davinci-002",
            prompt=full_prompt,
            max_tokens=100,
            temperature=0.5,
        )

        rewritten_prompt = response.choices[0].text.strip()
        await ctx.send(f"Rewritten Prompt: {rewritten_prompt}")

async def setup(bot):
    await bot.add_cog(AIPromptGenerator(bot))
