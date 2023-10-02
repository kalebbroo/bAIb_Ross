from typing import List, Tuple, Dict
from PIL import Image
from io import BytesIO
import discord
from discord.ext import commands

class ImageGrid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_quadrant = 0  # To keep track of the current quadrant (0 to 3)
        self.coordinates = []  # To store precomputed coordinates for each quadrant

    def initialize_grid(self, image_size=(1024, 1024)):
        grid_size = 2  # 2x2 grid
        border_size = 25  # Border size
        width, height = image_size
        total_width = (width + border_size) * grid_size + border_size
        total_height = (height + border_size) * grid_size + border_size
        self.grid_image = Image.new('RGB', (total_width, total_height), (54, 57, 63))
        self.coordinates = [(col * (width + border_size) + border_size, row * (height + border_size) + border_size) 
                            for row in range(grid_size) for col in range(grid_size)]

    async def image_grid(self, new_image: Image.Image, interaction, is_preview: bool, payload: Dict) -> Tuple[discord.Embed, discord.File]:
        if self.current_quadrant >= 4:
            self.current_quadrant = 0

        if not hasattr(self, 'grid_image') or self.current_quadrant == 0:
            self.initialize_grid()

        x, y = self.coordinates[self.current_quadrant]
        border_size = 25  # Change border size
        border_color = 'yellow' if is_preview else 'green'

        # Resize new_image to fit into the grid
        new_image = new_image.resize((1024, 1024))

        bordered_image = Image.new('RGB', (new_image.size[0] + 2 * border_size, new_image.size[1] + 2 * border_size), border_color)
        bordered_image.paste(new_image, (border_size, border_size))
        self.grid_image.paste(bordered_image, (x - border_size, y - border_size))

        if not is_preview:
            self.current_quadrant += 1  # Move to the next quadrant if the image is final

        # Resize the image grid to 15% of its original size for speed
        new_size = tuple(int(dim * 0.15) for dim in self.grid_image.size)
        resized_grid_image = self.grid_image.resize(new_size)

        image_file = BytesIO()
        resized_grid_image.save(image_file, format='PNG')
        image_file.seek(0)

        model_name = payload.get('model', 'Unknown')
        width = payload.get('width', 'Unknown')
        height = payload.get('height', 'Unknown')
        seed = payload.get('seed', 'Unknown')
        prompt = payload.get('prompt', 'Unknown')
        negative = payload.get('negativeprompt', 'Unknown')
        images = payload.get('images', 'Unknown')
        steps = payload.get('steps', 'Unknown')
        cfgscale = payload.get('cfgscale', 'Unknown')

        embed = discord.Embed(title="**Choose Your Favorite**", description=f"Generated using Model: {model_name}", color=0x00ff00) 
        embed.set_footer(text=f"Size: {width}x{height} | Seed: {seed} | Steps: {steps} | Cfg Scale: {cfgscale}")

        file = discord.File(image_file, filename="image_grid.png")
        embed.set_image(url=f"attachment://{file.filename}")

        return embed, file

async def setup(bot):
    await bot.add_cog(ImageGrid(bot))