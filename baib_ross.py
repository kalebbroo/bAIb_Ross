#Main bot file
import requests
import json

def create_txt2image(prompt, negative, steps, seed, cfg_scale, width, height):
    url = "http://localhost:7860/sdapi/v1/txt2img"  # replace with the correct URL
    headers = {"Content-Type": "application/json"}  # replace with the correct headers
    data = {
        "prompt": prompt,
        "negative_prompt": negative,
        "steps": steps,
        "seed": seed,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None
      
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
  
  
  from discord import Option, OptionType, SlashCommand

@bot.slash_command(
    name="generate",
    description="Generate an image using the Stable Diffusion API",
    options=[
        Option(
            name="prompt",
            description="The prompt for the image",
            type=OptionType.string,
            required=True,
        ),
        Option(
            name="model",
            description="The model to use",
            type=OptionType.string,
            required=True,
        ),
        Option(
            name="steps",
            description="The number of steps to use",
            type=OptionType.integer,
            required=True,
        ),
        Option(
            name="seed",
            description="The seed to use",
            type=OptionType.integer,
            required=True,
        ),
        Option(
            name="negative",
            description="Negative prompts to avoid",
            type=OptionType.string,
            required=False,
        ),
        Option(
            name="width",
            description="The width of the image",
            type=OptionType.integer,
            required=False,
        ),
        Option(
            name="height",
            description="The height of the image",
            type=OptionType.integer,
            required=False,
        ),
        Option(
            name="cfg_scale",
            description="The CFG scale to use",
            type=OptionType.float,
            required=False,
        ),
        Option(
            name="sampling_method",
            description="The sampling method to use",
            type=OptionType.string,
            required=False,
        ),
        Option(
            name="web_ui_styles",
            description="The Web UI styles to use",
            type=OptionType.string,
            required=False,
        ),
        Option(
            name="extra_networks",
            description="The extra networks to use",
            type=OptionType.string,
            required=False,
        ),
        Option(
            name="face_restoration",
            description="Whether to use face restoration",
            type=OptionType.boolean,
            required=False,
        ),
        Option(
            name="high_res_fix",
            description="Whether to use high-res fix",
            type=OptionType.boolean,
            required=False,
        ),
        Option(
            name="clip_skip",
            description="Whether to use CLIP skip",
            type=OptionType.boolean,
            required=False,
        ),
        Option(
            name="img2img",
            description="Whether to use img2img",
            type=OptionType.boolean,
            required=False,
        ),
        Option(
            name="denoising_strength",
            description="The denoising strength to use",
            type=OptionType.float,
            required=False,
        ),
        Option(
            name="batch_count",
            description="The batch count to use",
            type=OptionType.integer,
            required=False,
        ),
    ],
)
async def generate(ctx, prompt: str, model: str, steps: int, seed: int, negative: str = None, width: int = None, height: int = None, cfg_scale: float = None, sampling_method: str = None, web_ui_styles: str = None, extra_networks: str = None, face_restoration: bool = None, high_res_fix: bool = None, clip_skip: bool = None, img2img: bool = None, denoising_strength: float = None, batch_count:I apologize for the cut-off in the previous message. Here is the complete function:

```python
async def generate(ctx, prompt: str, model: str, steps: int, seed: int, negative: str = None, width: int = None, height: int = None, cfg_scale: float = None, sampling_method: str = None, web_ui_styles: str = None, extra_networks: str = None, face_restoration: bool = None, high_res_fix: bool = None, clip_skip: bool = None, img2img: bool = None, denoising_strength: float = None, batch_count: int = None):
    # Call the text2image function with the provided options
    image = await text2image(prompt, model, steps, seed, negative, width, height, cfg_scale, sampling_method, web_ui_styles, extra_networks, face_restoration, high_res_fix, clip_skip, img2img, denoising_strength, batch_count)
    
    # Save the image and post it to the showcase channel
    await save_and_showcase_image(ctx, image, prompt, model, steps, seed, negative, width, height, cfg_scale, sampling_method, web_ui_styles, extra_networks, face_restoration, high_res_fix, clip_skip, img2img, denoising_strength, batch_count)

                   
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
