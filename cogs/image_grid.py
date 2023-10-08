from typing import List, Tuple, Dict
from discord.ext import commands
from datetime import datetime
from io import BytesIO
from PIL import Image
import discord
import os

class ImageGrid(commands.Cog):
    """A class for generating the image grid."""
    def __init__(self, bot: commands.Bot):
        """Initialize the image grid and associated variables."""
        self.bot = bot
        self.current_quadrant = 0  # To keep track of the current quadrant (0 to 3)
        self.coordinates = []  # To store coordinates for each quadrant

    def initialize_grid(self, image_size: Tuple[int, int]) -> None:
        """Initialize the image grid with a given image size.
        Args:
            image_size: The size of each individual image in the grid.
        """
        grid_size = 2  # 2x2 grid
        border_size = 25  # Border size in pixels
        width, height = image_size
        total_width = (width + border_size) * grid_size + border_size
        total_height = (height + border_size) * grid_size + border_size

        # Create a new blank grid image
        self.grid_image = Image.new('RGB', (total_width, total_height), (54, 57, 63))

        # Calculate coordinates for pasting individual images into the grid
        self.coordinates = [
            (col * (width + border_size) + border_size, row * (height + border_size) + border_size) 
            for row in range(grid_size) 
            for col in range(grid_size)
        ]

    async def image_grid(self, new_image: Image.Image, interaction, is_preview: bool, payload: Dict) -> Tuple[discord.Embed, discord.File]:
        """Generate an image grid and return it along with an embed.
        Args:
            new_image: The new image to add to the grid.
            interaction: The Discord interaction that triggered this.
            is_preview: Whether the image is a preview or final.
            payload: Additional data for the embed.
        Returns:
            A tuple containing the Discord embed and file.
        """
        # Dynamically resize the new image based on the payload This is needed because preview images are smaller.
        # TODO: Make this more efficient by only running it IF the image is a preview
        width = payload.get('width', 1024)
        height = payload.get('height', 1024)
        new_image = new_image.resize((width, height))

        # Reset the quadrant if it exceeds the maximum
        if self.current_quadrant >= 4:
            self.current_quadrant = 0

        # Initialize the grid if it doesn't exist or we're back to the first quadrant
        if not hasattr(self, 'grid_image') or self.current_quadrant == 0:
            self.initialize_grid((width, height))

        # Get the coordinates for the current quadrant
        x, y = self.coordinates[self.current_quadrant]
        
        # Border settings
        border_size = 25  # Border size in pixels
        border_color = 'yellow' if is_preview else 'green'  # Border color based on whether it's a preview or not

        # Add a border to the new image
        bordered_image = Image.new('RGB', (new_image.size[0] + 2 * border_size, new_image.size[1] + 2 * border_size), border_color)
        bordered_image.paste(new_image, (border_size, border_size))

        # Paste the new image into the grid
        self.grid_image.paste(bordered_image, (x - border_size, y - border_size))

        # Save the final images to disk
        if not is_preview:
            # Increment the current quadrant for the next image
            self.current_quadrant += 1
            # Save the final images to disk
            username = interaction.user.name
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H-%M-%S")
            prompt_words = payload.get('prompt', '').split()[:3]
            folder_name = f"images/{username}/{date_str}"

            # Create the directory if it doesn't exist
            os.makedirs(folder_name, exist_ok=True)

            # Save the image
            image_path = os.path.join(folder_name, f"{'-'.join(prompt_words)}-{time_str}.jpg")
            new_image.save(image_path)

        # Resize the grid image for quick Discord uploading (Optional)
        new_size = tuple(int(dim * 0.45) for dim in self.grid_image.size)
        resized_grid_image = self.grid_image.resize(new_size)

        # Convert the PIL image to a Discord-friendly file
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

        # Create the embed
        model_name = payload.get('model', 'Unknown')
        embed = discord.Embed(title="**Upscale Your Favorite Image**", description=f"Generated using Model: {model_name}", color=0x00ff00)
        embed.set_footer(text=f"Size: {width}x{height} | Seed: {seed} | Steps: {steps} | Cfg Scale: {cfgscale}")

        # Attach the image file to the embed
        file = discord.File(image_file, filename="image_grid.png")
        embed.set_image(url=f"attachment://{file.filename}")

        return embed, file

async def setup(bot: commands.Bot) -> None:
    """Setup the Cog.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(ImageGrid(bot))
