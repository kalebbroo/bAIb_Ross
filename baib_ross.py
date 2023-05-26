#Main bot file
import requests
import json
import discord
from discord import Option, OptionType, SlashCommand
import PIL
from GPT_prompt import GPT
from discord import ButtonStyle, Interaction
from discord.ui import Button, View






await bot.add_cog(GPT(bot))



      
def upscale_image(image_path):
    url = "http://localhost:7860/sdapi/v1/img2img"  # replace with the correct URL
    headers = {"Content-Type": "application/json"}  # replace with the correct headers

    # Read the image file and convert it to base64
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

    data = {
        "image": encoded_string
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None
      
async def save_image_to_showcase_channel(image_data, info, channel_id):
    # Convert the base64 image data to bytes
    image_bytes = base64.b64decode(image_data)
    image_file = discord.File(BytesIO(image_bytes), filename="upscaled_image.png")

    # Create an embed with the image information
    embed = discord.Embed(title="Upscaled Image", description="Here's an upscaled image!")
    embed.add_field(name="Steps", value=info['steps'], inline=True)
    embed.add_field(name="Seed", value=info['seed'], inline=True)
    embed.add_field(name="Model", value=info['model'], inline=True)
    embed.add_field(name="Prompt", value=info['prompt'], inline=True)
    embed.add_field(name="Negative", value=info['negative'], inline=True)
    embed.set_image(url="attachment://upscaled_image.png")

    # Get the showcase channel
    channel = bot.get_channel(channel_id)

    # Send the embed to the showcase channel
    message = await channel.send(file=image_file, embed=embed)

    # Start a new thread for the image
    thread = await message.start_thread(name="Discussion for upscaled image")

    return thread
  

                   


class ImageView(View):
    def __init__(self, ctx, image_urls):
        super().__init__()
        self.ctx = ctx
        self.image_urls = image_urls

    @Button(label="Choose for img2img", style=ButtonStyle.primary)
    async def choose_for_img2img(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for choosing one of the images for img2img
        pass

    @Button(label="Upscale and save", style=ButtonStyle.primary)
    async def upscale_and_save(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for upscaling and saving the image
        pass

    @Button(label="Regenerate", style=ButtonStyle.primary)
    async def regenerate(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for regenerating the image
        pass

    @Button(label="Delete", style=ButtonStyle.danger)
    async def delete(self, button: Button, interaction: Interaction):
        # Delete the message
        await self.ctx.message.delete()

# Create the view and add it to the message
view = ImageView(ctx, image_urls)
await msg.edit(view=view)

                  
from discord import ButtonStyle, Interaction
from discord.ui import Button, View

class ImageView(View):
    def __init__(self, ctx, image_urls):
        super().__init__()
        self.ctx = ctx
        self.image_urls = image_urls

    @Button(label="Choose for img2img", style=ButtonStyle.primary)
    async def choose_for_img2img(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for choosing one of the images for img2img
        pass

    @Button(label="Upscale and save", style=ButtonStyle.primary)
    async def upscale_and_save(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for upscaling and saving the image
        pass

    @Button(label="Regenerate", style=ButtonStyle.primary)
    async def regenerate(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for regenerating the image
        pass

    @Button(label="Delete", style=ButtonStyle.danger)
    async def delete(self, button: Button, interaction: Interaction):
        # Delete the message
        await self.ctx.message.delete()

    @Button(label="Edit Prompt", style=ButtonStyle.secondary)
    async def edit_prompt(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for editing the prompt
        pass

    @Button(label="Randomize Seed", style=ButtonStyle.secondary)
    async def randomize_seed(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for randomizing the seed
        pass

    @Button(label="View Info", style=ButtonStyle.secondary)
    async def view_info(self, button: Button, interaction: Interaction):
        # Here you would implement the logic for viewing the image's information
        pass

# Create the view and add it to the message
view = ImageView(ctx, image_urls)
await msg.edit(view=view)
