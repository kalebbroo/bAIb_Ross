import discord
from discord.ext import commands
from discord import app_commands
from baib_ross import showcase
from config import SHOWCASE_ID

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready!")

    @commands.command()
    async def sync(self, ctx) -> None:
        fmt  = await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"synced {len(fmt)} commands")
        


    @app_commands.command(name="dream", description="Generate an image using the Stable Diffusion API")
    @app_commands.describe(prompt = "Enter the text prompt that you want the image to be generated from")
    @app_commands.describe(negative = "Enter any negative prompts to avoid certain elements in the image")
    @app_commands.describe(model = "Choose the model to be used for image generation")
    @app_commands.describe(steps = "Specify the number of steps for the diffusion process")
    @app_commands.describe(seed = "Provide a seed for the random number generator to ensure reproducibility")
    @app_commands.describe(width = "Specify the width of the generated image")
    @app_commands.describe(height = "Specify the height of the generated image")
    @app_commands.describe(sampling_method = "Choose the sampling method for the diffusion process")
    @app_commands.describe(cfg_scale = "Specify the configuration scale for the model")
    @app_commands.describe(face_restoration = "Choose whether to apply face restoration to the generated image")
    @app_commands.describe(high_res_fix = "Choose whether to apply high resolution fix to the generated image")
    @app_commands.describe(denoising_strength = "Specify the strength of denoising to be applied to the generated image")
    async def dream(self, interaction: discord.Interaction, prompt: str = None, negative: str = None, model: str = None, steps: int = 20,
                    seed: int = -1, width: int = 512, height: int = 512, sampling_method: str = None, cfg_scale: int = 7,
                    face_restoration: bool = False, high_res_fix: bool = False, denoising_strength: float = 0.7):
        # Call the text2image function with the provided options
        payload = self.bot.get_cog('Text2Image').create_payload(prompt, negative, steps, seed, cfg_scale, width, height)

        image_data = await self.bot.get_cog('Text2Image').txt2image(payload)
        image_file = await self.bot.get_cog('Text2Image').pull_image(image_data)
        #await interaction.channel.send(file=image_file)
        description = prompt
        embed = await create_embed(image_file, description, interaction)
        await interaction.channel.send(embed=embed)

        # Save the image and post it to the showcase channel
        #await showcase(self.bot, image, {"steps": steps, "seed": seed, "model": model, "prompt": prompt, "negative": negative}, SHOWCASE_ID)



async def create_embed(image_file, description, interaction):
        embed = discord.Embed(color=6301830,
                                description=description)
        # Attach file to embed
        embed.set_image(url="attachment://temp.png")

        await interaction.channel.send(embed=embed, file=image_file)



async def setup(bot):
    await bot.add_cog(Commands(bot))
    