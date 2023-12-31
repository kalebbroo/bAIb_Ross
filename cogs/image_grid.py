from typing import List, Tuple, Dict
from discord.ext import commands
from datetime import datetime
from io import BytesIO
from PIL import Image
import base64
import discord
import time
import os

class ImageGrid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    async def upscale(self, message, encoded_image, user: discord.User):
        """Upscale an image using the API."""
        try:
            if not encoded_image:
                await message.channel.send("No encoded image provided for upscaling.")
                return
            # Decode the base64 string to get the image
            image_data = base64.b64decode(encoded_image)
            image = Image.open(BytesIO(image_data))

            # Check the size of the image
            width, height = image.size
            max_dimension = 2048
            if width > max_dimension or height > max_dimension:
                await message.channel.send(
                    embed=discord.Embed(
                        title="Upscale Cancelled",
                        description="The image size exceeds the maximum allowed dimensions (2048x2048) for upscaling.",
                        color=discord.Color.red()
                    ).set_footer(text=f"Requested by {user.display_name}", icon_url=user.avatar.url)
                )
                return

            session_id = await self.bot.get_cog('APICalls').get_session()
            payload = self.bot.get_cog('APICalls').create_payload(
                session_id, init_image=encoded_image, init_image_creativity=0.3,
                width=width * 2, height=height * 2, upscale=True, images=1, steps=40, cfgscale=10, batchsize=1
            )

            buttons = self.bot.get_cog("Buttons")
            embed = discord.Embed(
                title="Image Upscaling",
                description="Ready to upscale the uploaded image.",
                color=discord.Color.orange()
            ).set_footer(text=f"Requested by {user.display_name}", icon_url=user.avatar.url)

            view = buttons.ConfirmationView(self.bot, payload, user.id)
            await message.channel.send(embed=embed, view=view)

        except Exception as e:
            print(f"Error while processing the image: {e}")
            await message.channel.send("An error occurred while processing the image.")


    async def img2img(self, message, encoded_image, user: discord.User):
        """Generate an image based on the input image."""
        try:
            if not encoded_image:
                await message.channel.send("No image found or provided for image-to-image generation.")
                return

            # Decode the base64 string to get the image
            image_data = base64.b64decode(encoded_image)
            image = Image.open(BytesIO(image_data))

            # Get the size of the image
            width, height = image.size

            session_id = await self.bot.get_cog('APICalls').get_session()
            payload = self.bot.get_cog('APICalls').create_payload(
                session_id, init_image=encoded_image, init_image_creativity=0.6,
                width=width, height=height
            )
            buttons = self.bot.get_cog("Buttons")
            embed = discord.Embed(
                title="Image to Image Generation",
                description="Create an image based on the uploaded image.",
                color=discord.Color.green()
            ).set_footer(text=f"Requested by {user.display_name}", icon_url=user.avatar.url)

            view = buttons.ConfirmationView(self.bot, payload, user.id)
            await message.channel.send(embed=embed, view=view)

        except Exception as e:
            print(f"Error while processing the image: {e}")
            await message.channel.send("An error occurred while processing the image.")


    def get_session_state(self, interaction_id, payload):
        """Get the session state for a specific interaction."""
        if interaction_id not in self.sessions:
            self.sessions[interaction_id] = {
                "preview_images": [],
                "final_images": [],
                "message": None,
                "num_images_expected": 4,  # 4 images per batch
                "payload": payload
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

    async def process_image(self, interaction, new_image, is_preview, message, payload):
        """Process and update images in a message."""
        state = self.get_session_state(interaction.id, payload)

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

async def setup(bot: commands.Bot) -> None:
    """Setup the Cog.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(ImageGrid(bot))
