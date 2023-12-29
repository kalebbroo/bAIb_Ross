from typing import List, Tuple, Dict
from discord.ext import commands
from datetime import datetime
from io import BytesIO
from PIL import Image
import discord
import time
import os

#TODO: 1. create an embed that attaches the first 4 preview images. images should not be embedded in the embed, but attached to the embed.
#TODO: 2. figure out how to tell the placement of each preview image. for example the first image is always in the top left corner.
#TODO: 3. Update the embed with the next batch of 4 preview images
#TODO: 4. Update the embed with the final image

class ImageGrid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    def get_session_state(self, interaction_id):
        """Get the session state for a specific interaction."""
        if interaction_id not in self.sessions:
            self.sessions[interaction_id] = {
                "preview_images": [],
                "final_images": [],
                "message": None,
                "num_images_expected": 4  # 4 images per batch
            }
        return self.sessions[interaction_id]
    
    def create_grid(self, image_files):
        images = []
        for idx, file in enumerate(image_files):
            # Create a new BytesIO object for each file
            file.fp.seek(0)  # Ensure the pointer is at the start of the stream
            image_stream = BytesIO(file.fp.read())  # Read the content into a new BytesIO object
            image = Image.open(image_stream)
            images.append(image)

        # Make a new image grid
        width, height = images[0].size
        grid = Image.new('RGB', (width * 2, height * 2))

        # Paste images onto the grid
        grid.paste(images[0], (0, 0))
        grid.paste(images[1], (width, 0))
        grid.paste(images[2], (0, height))
        grid.paste(images[3], (width, height))

        # Convert grid to BytesIO for Discord
        grid_io = BytesIO()
        grid.save(grid_io, format='PNG')
        grid_io.seek(0)

        # Generate a unique filename using a timestamp
        unique_filename = f"grid-{int(time.time())}.png"
        return grid_io, unique_filename
    
    def embed_grid(self, grid_io):
        file = discord.File(fp=grid_io, filename="grid.png")
        embed = discord.Embed(title="Image Preview", description="Here's a preview of your images.")
        embed.set_image(url="attachment://grid.png")
        return embed, file

    async def process_image(self, interaction, new_image, is_preview, message):
        """Process and update images in a message."""
        state = self.get_session_state(interaction.id)

        # Convert the PIL image to a Discord-friendly file
        image_file = BytesIO()
        new_image.save(image_file, format='PNG')
        image_file.seek(0)
        filename = f"image-{len(state['preview_images']) + 1}-{int(time.time())}.png"  # Unique filename
        file = discord.File(fp=image_file, filename=filename)

        # Add to the appropriate list
        if is_preview:
            state["preview_images"].append(file)

            # Check if four preview images have been received
            if len(state["preview_images"]) == state["num_images_expected"]:
                # Process the set of four preview images
                grid_io, grid_filename = self.create_grid(state["preview_images"])
                embed, grid_file = self.embed_grid(grid_io)
                state["message"] = message
                if state["message"]:
                    # Edit the existing message with the new grid and embed
                    state["message"] = await state["message"].edit(embed=embed, attachments=[discord.File(fp=grid_io, filename=grid_filename)])
                else:
                    # If there's no previous message, send a new one
                    state["message"] = await interaction.followup.send(embed=embed, file=grid_file)

                # Clear the list of preview images for the next set
                state["preview_images"].clear()

        else:
            state["final_images"].append(file)
            if len(state["final_images"]) == state["num_images_expected"]:
                # Save final images
                self.save_final_images(interaction, state["final_images"])

                # Prepare buttons for the final image embed
                buttons_view = self.bot.get_cog("Buttons").ImageButtons(self.bot, interaction, state['payload'], message.id)

                # Edit or send a new message with final images and buttons
                current_embed = message.embeds[0] if message.embeds else discord.Embed()
                if state["message"]:
                    state["message"] = await state["message"].edit(embed=current_embed, attachments=state["final_images"], view=buttons_view)
                else:
                    state["message"] = await interaction.followup.send(embed=current_embed, files=state["final_images"], view=buttons_view)
                state["final_images"].clear()  # Clear final images list

    def save_final_images(self, interaction, image_files):
        """Save final images to disk."""
        username = interaction.user.name
        message_id = interaction.message.id
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H-%M-%S")
        folder_name = f"images/{username}/{date_str}/{message_id}"

        os.makedirs(folder_name, exist_ok=True)

        for idx, file in enumerate(image_files):
            # You might want to include idx in the filename to differentiate between images
            image_path = os.path.join(folder_name, f"final-image-{idx+1}-{time_str}.png")
            file.fp.seek(0)  # Reset file pointer
            with open(image_path, "wb") as img_file:
                img_file.write(file.fp.read())
            file.fp.seek(0) # Reset file pointer 

        print(f"Saved final images for {username} on {date_str}")


# class ImageGrid(commands.Cog):
#     """A class for generating the image grid."""
#     def __init__(self, bot: commands.Bot):
#         """Initialize the image grid and associated variables."""
#         self.bot = bot
#         self.current_quadrant = 0  # To keep track of the current quadrant (0 to 3)
#         self.coordinates = []  # To store coordinates for each quadrant

#     def initialize_grid(self, image_size: Tuple[int, int]) -> None:
#         """Initialize the image grid with a given image size.
#         Args:
#             image_size: The size of each individual image in the grid.
#         """
#         grid_size = 2  # 2x2 grid
#         border_size = 25  # Border size in pixels
#         width, height = image_size
#         total_width = (width + border_size) * grid_size + border_size
#         total_height = (height + border_size) * grid_size + border_size

#         # Create a new blank grid image
#         self.grid_image = Image.new('RGB', (total_width, total_height), (54, 57, 63))

#         # Calculate coordinates for pasting individual images into the grid
#         self.coordinates = [
#             (col * (width + border_size) + border_size, row * (height + border_size) + border_size) 
#             for row in range(grid_size) 
#             for col in range(grid_size)
#         ]

#     async def upscale_embed(self, new_image: Image.Image, interaction, is_preview: bool, payload: Dict, message_id=None) -> Tuple[discord.Embed, discord.File]:
#         """Generate a single upscaled image and return it with an embed.
#         Args:
#             new_image: The new image to add to the embed.
#             interaction: The Discord interaction that triggered this.
#             is_preview: Whether the image is a preview or final.
#             payload: Additional data for the embed.
#         Returns:
#             A tuple containing the Discord embed and file.
#         """
#         # Save the final images to disk
#         if not is_preview:
#             username = interaction.user.name
#             date_str = datetime.now().strftime("%Y-%m-%d")
#             time_str = datetime.now().strftime("%H-%M-%S")
#             prompt_words = payload.get('prompt', '').split()[:5]
#             folder_name = f"images/{username}/{date_str}/upscaled"

#             os.makedirs(folder_name, exist_ok=True)
#             image_path = os.path.join(folder_name, f"{'-'.join(prompt_words)}-{time_str}.jpg")
#             new_image.save(image_path)

#             # Access the message_data dictionary
#             message_data = self.bot.get_cog('APICalls').message_data

#             # Update the image_files dictionary using message_id
#             if message_id not in message_data:
#                 message_data[message_id] = {'payload': payload, 'user_id': interaction.user.id, 'image_files': []}

#             if 'image_files' not in message_data[message_id]:
#                 message_data[message_id]['image_files'] = []

#             message_data[message_id]['image_files'].append(image_path)
#             print(f"Image paths: {message_data[message_id]['image_files']}")

#         # Convert the PIL image to a Discord-friendly file
#         image_file = BytesIO()
#         new_image.save(image_file, format='PNG')
#         image_file.seek(0)

#         model_name = payload.get('model', 'Unknown')
#         width = payload.get('width', 'Unknown')
#         height = payload.get('height', 'Unknown')
#         seed = payload.get('seed', 'Unknown')
#         prompt = payload.get('prompt', 'Unknown')
#         negative = payload.get('negativeprompt', 'Unknown')
#         images = payload.get('images', 'Unknown')
#         steps = payload.get('steps', 'Unknown')
#         cfgscale = payload.get('cfgscale', 'Unknown')

#         # Create the embed
#         model_name = payload.get('model', 'Unknown')
#         embed = discord.Embed(title="**Here is your upscaled image!**", description=f"Generated using Model: {model_name}", color=0x00ff00)
#         embed.set_footer(text=f"Size: {width}x{height} | Seed: {seed} | Steps: {steps} | Cfg Scale: {cfgscale}")

#         # Attach the image file to the embed
#         file = discord.File(image_file, filename="upscaled_image.png")
#         embed.set_image(url=f"attachment://{file.filename}")

#         return embed, file

    # async def image_grid(self, new_image: Image.Image, interaction, is_preview: bool, payload: Dict, message_id=None) -> Tuple[discord.Embed, discord.File]:
    #     """Generate an image grid and return it along with an embed.
    #     Args:
    #         new_image: The new image to add to the grid.
    #         interaction: The Discord interaction that triggered this.
    #         is_preview: Whether the image is a preview or final.
    #         payload: Additional data for the embed.
    #     Returns:
    #         A tuple containing the Discord embed and file.
    #     """
    #     upscale = payload.get('upscale', False)
    #     if upscale:
    #         embed, file = await self.upscale_embed(new_image, interaction, is_preview, payload, message_id)
    #         return embed, file

    #     # Dynamically resize the new image based on the payload This is needed because preview images are smaller.
    #     # TODO: Make this more efficient by only running it IF the image is a preview
    #     width = payload.get('width', 1024)
    #     height = payload.get('height', 1024)
    #     new_image = new_image.resize((width, height))

    #     # Reset the quadrant if it exceeds the maximum
    #     if self.current_quadrant >= 4:
    #         self.current_quadrant = 0

    #     # Initialize the grid if it doesn't exist or we're back to the first quadrant
    #     if not hasattr(self, 'grid_image') or self.current_quadrant == 0:
    #         self.initialize_grid((width, height))

    #     # Get the coordinates for the current quadrant
    #     x, y = self.coordinates[self.current_quadrant]
        
    #     # Border settings
    #     border_size = 25  # Border size in pixels
    #     border_color = 'yellow' if is_preview else 'green'  # Border color based on whether it's a preview or not

    #     # Add a border to the new image
    #     bordered_image = Image.new('RGB', (new_image.size[0] + 2 * border_size, new_image.size[1] + 2 * border_size), border_color)
    #     bordered_image.paste(new_image, (border_size, border_size))

    #     # Paste the new image into the grid
    #     self.grid_image.paste(bordered_image, (x - border_size, y - border_size))

    #     try:
    #         # Save the final images to disk
    #         if not is_preview:
    #             self.current_quadrant += 1
    #             username = interaction.user.name
    #             date_str = datetime.now().strftime("%Y-%m-%d")
    #             time_str = datetime.now().strftime("%H-%M-%S")
    #             prompt_words = payload.get('prompt', '').split()[:3]
    #             folder_name = f"images/{username}/{date_str}/{message_id}"

    #             os.makedirs(folder_name, exist_ok=True)
    #             image_path = os.path.join(folder_name, f"{'-'.join(prompt_words)}-{time_str}.jpg")
    #             new_image.save(image_path)

    #             # Access the message_data dictionary
    #             message_data = self.bot.get_cog('APICalls').message_data

    #             # Update the image_files dictionary using message_id
    #             if message_id not in message_data:
    #                 message_data[message_id] = {'payload': payload, 'user_id': interaction.user.id, 'image_files': []}

    #             if 'image_files' not in message_data[message_id]:
    #                 message_data[message_id]['image_files'] = []

    #             message_data[message_id]['image_files'].append(image_path)
    #             print(f"Image paths: {message_data[message_id]['image_files']}")

    #     except Exception as e:
    #         print(f"An exception occurred: {e}")
    #         import traceback
    #         traceback.print_exc()

    #     # Resize the grid image for quick Discord uploading (Optional)
    #     new_size = tuple(int(dim * 0.45) for dim in self.grid_image.size)
    #     resized_grid_image = self.grid_image.resize(new_size)

    #     # Convert the PIL image to a Discord-friendly file
    #     image_file = BytesIO()
    #     resized_grid_image.save(image_file, format='PNG')
    #     image_file.seek(0)

    #     model_name = payload.get('model', 'Unknown')
    #     width = payload.get('width', 'Unknown')
    #     height = payload.get('height', 'Unknown')
    #     seed = payload.get('seed', 'Unknown')
    #     prompt = payload.get('prompt', 'Unknown')
    #     negative = payload.get('negativeprompt', 'Unknown')
    #     images = payload.get('images', 'Unknown')
    #     steps = payload.get('steps', 'Unknown')
    #     cfgscale = payload.get('cfgscale', 'Unknown')

    #     # Create the embed
    #     model_name = payload.get('model', 'Unknown')
    #     embed = discord.Embed(title="**Upscale Your Favorite Image**", description=f"Generated using Model: {model_name}", color=0x00ff00)
    #     embed.set_footer(text=f"Size: {width}x{height} | Seed: {seed} | Steps: {steps} | Cfg Scale: {cfgscale}")

    #     # Attach the image file to the embed
    #     file = discord.File(image_file, filename="image_grid.png")
    #     embed.set_image(url=f"attachment://{file.filename}")

    #     return embed, file

async def setup(bot: commands.Bot) -> None:
    """Setup the Cog.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(ImageGrid(bot))
