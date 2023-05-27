from discord.ext import commands, app_commands

class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="dream", description="Generate an image using the Stable Diffusion API")
    @app_commands.describe(prompt = "Enter the text prompt that you want the image to be generated from")
    @app_commands.describe(negative = "Enter any negative prompts to avoid certain elements in the image")
    @app_commands.describe(model = "Choose the model to be used for image generation")
    @app_commands.describe(steps = "Specify the number of steps for the diffusion process")
    @app_commands.describe(seed = "Provide a seed for the random number generator to ensure reproducibility")
    @app_commands.describe(width = "Specify the width of the generated image")
    @app_commands.describe(height = "Specify the height of the generated image")
    @app_commands.describe(sampling = "Choose the sampling method for the diffusion process")
    @app_commands.describe(cfg = "Specify the configuration scale for the model")
    @app_commands.describe(face_restoration = "Choose whether to apply face restoration to the generated image")
    @app_commands.describe(high_res_fix = "Choose whether to apply high resolution fix to the generated image")
    @app_commands.describe(denoising_strength = "Specify the strength of denoising to be applied to the generated image")
    async def generate(self, ctx: commands.Context, prompt: str, model: str, steps: int, seed: int, negative: str = None, width: int = None, height: int = None, cfg: float = None, sampling: str = None, face_restoration: bool = None, high_res_fix: bool = None, denoising_strength: float = None):
        # Call the text2image function with the provided options
        image = await self.bot.get_cog('text2image').txt2image(prompt, negative, steps, seed, cfg, width, height)
        
        # Save the image and post it to the showcase channel
        await self.bot.get_cog('bAIb_Ross').save_image_to_showcase_channel(image, prompt, model, steps, seed, negative, width, height, cfg, sampling, face_restoration, high_res_fix, denoising_strength)

def setup(bot: commands.Bot) -> None:
    bot.add_cog(Commands(bot))