import os
import discord
from discord.ext import commands
from discord.ext.commands import Bot as BotBase
import aiohttp
from io import BytesIO
from PIL import Image
import base64


class Text2Image(commands.Cog):
    bot: BotBase

    def __init__(self, bot):
        self.bot = bot

        @commands.Cog.listener()
        async def on_ready(self):
            print("Bot is ready!")



    @staticmethod
    def create_payload(prompt, negative, steps, seed, cfg_scale, width, height, enable_hr=False, denoising_strength=0, firstphase_width=0,
                    firstphase_height=0, hr_scale=2, hr_upscaler="",
                    hr_second_pass_steps=0, hr_resize_x=0, hr_resize_y=0, styles=[], subseed=-1, subseed_strength=0,
                    seed_resize_from_h=-1, seed_resize_from_w=-1, sampler_name="DPM++ 2S a Karras",
                    batch_size=4, n_iter=1, restore_faces=False, tiling=False, eta=0,
                    s_churn=0, s_tmax=0, s_tmin=0, s_noise=1, override_settings={},
                    override_settings_restore_afterwards=True, script_args=[], sampler_index="Euler"):
        return {
            "enable_hr": enable_hr,
            "denoising_strength": denoising_strength,
            "firstphase_width": firstphase_width,
            "firstphase_height": firstphase_height,
            "hr_scale": hr_scale,
            "hr_upscaler": hr_upscaler,
            "hr_second_pass_steps": hr_second_pass_steps,
            "hr_resize_x": hr_resize_x,
            "hr_resize_y": hr_resize_y,
            "prompt": prompt,
            "styles": styles,
            "seed": seed,
            "subseed": subseed,
            "subseed_strength": subseed_strength,
            "seed_resize_from_h": seed_resize_from_h,
            "seed_resize_from_w": seed_resize_from_w,
            "sampler_name": sampler_name,
            "batch_size": batch_size,
            "n_iter": n_iter,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
            "restore_faces": restore_faces,
            "tiling": tiling,
            "negative_prompt": negative,
            "eta": eta,
            "s_churn": s_churn,
            "s_tmax": s_tmax,
            "s_tmin": s_tmin,
            "s_noise": s_noise,
            "override_settings": override_settings,
            "override_settings_restore_afterwards": override_settings_restore_afterwards,
            "script_args": script_args,
            "sampler_index": sampler_index
        }

    @staticmethod
    async def txt2image(payload):
        url = "http://localhost:7860/sdapi/v1/txt2img"
        headers = {"Content-Type": "application/json"}

        print(f"Payload: {payload}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data
                else:
                    print(f"Error: {response.status}")
                    return None
                
    async def pull_image(self, response):
        # Get the list of images from the response
        images_data = response['images']

        # Decode each image and convert it to a PIL Image object
        images = [Image.open(BytesIO(base64.b64decode(image_data))) for image_data in images_data]

        # Determine the grid size based on the number of images
        grid_size = int(len(images) ** 0.5)

        # Create a new image of the appropriate size to hold the grid
        grid_image = Image.new('RGB', (grid_size * images[0].width, grid_size * images[0].height))

        # Place each image into the grid and save each image individually
        for i, image in enumerate(images):
            row = i // grid_size
            col = i % grid_size
            grid_image.paste(image, (col * image.width, row * image.height))
            folder_path = "image_cache"
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            image_path = os.path.join(folder_path, f"image_{i}.png")
            image.save(image_path)

        # Save the grid image to a BytesIO object
        image_file = BytesIO()
        grid_image.save(image_file, format='PNG')
        image_file.seek(0)

        # Wrap the BytesIO object in a File object for sending via Discord
        image_file = discord.File(image_file, filename="temp.png")

        return image_file


        
async def setup(bot):
    await bot.add_cog(Text2Image(bot))

