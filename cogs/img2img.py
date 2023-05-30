import aiohttp
import base64
import os
from io import BytesIO
from PIL import Image
from discord.ext import commands
import requests

class Image2Image(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def create_payload(init_images, resize_mode=0, denoising_strength=0.75, image_cfg_scale=0, mask="", mask_blur=4,
                       inpainting_fill=0, inpaint_full_res=True, inpaint_full_res_padding=0, inpainting_mask_invert=0,
                       initial_noise_multiplier=0, prompt="", styles=[], seed=-1, subseed=-1, subseed_strength=0,
                       seed_resize_from_h=-1, seed_resize_from_w=-1, sampler_name="DPM++ 2S a Karras", batch_size=1, n_iter=1,
                       steps=50, cfg_scale=7, width=512, height=512, restore_faces=False, tiling=False,
                       do_not_save_samples=False, do_not_save_grid=False, negative_prompt="", eta=0,
                       s_min_uncond=0, s_churn=0, s_tmax=0, s_tmin=0, s_noise=1, override_settings={},
                       override_settings_restore_afterwards=True, script_args=[], sampler_index="Euler",
                       include_init_images=False, script_name="", send_images=True, save_images=False,
                       alwayson_scripts={}):
        return {
            "init_images": init_images,
            "resize_mode": resize_mode,
            "denoising_strength": denoising_strength,
            "image_cfg_scale": image_cfg_scale,
            "mask": mask,
            "mask_blur": mask_blur,
            "inpainting_fill": inpainting_fill,
            "inpaint_full_res": inpaint_full_res,
            "inpaint_full_res_padding": inpaint_full_res_padding,
            "inpainting_mask_invert": inpainting_mask_invert,
            "initial_noise_multiplier": initial_noise_multiplier,
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
            "do_not_save_samples": do_not_save_samples,
            "do_not_save_grid": do_not_save_grid,
            "negative_prompt": negative_prompt,
            "eta": eta,
            "s_min_uncond": s_min_uncond,
            "s_churn": s_churn,
            "s_tmax": s_tmax,
            "s_tmin": s_tmin,
            "s_noise": s_noise,
            "override_settings": override_settings,
            "override_settings_restore_afterwards": override_settings_restore_afterwards,
            "script_args": script_args,
            "sampler_index": sampler_index,
            "include_init_images": include_init_images,
            "script_name": script_name,
            "send_images": send_images,
            "save_images": save_images,
            "alwayson_scripts": alwayson_scripts
        }


    @staticmethod
    async def img2img(payload):
        url = "http://localhost:7860/sdapi/v1/img2img"
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

    async def upscale_image(self, image_path, interaction):
        try:
            # Open the image and convert it to base64
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                # Add the prefix
                encoded_string = "data:image/png;base64," + encoded_string

        except FileNotFoundError:
            await interaction.response.send_message("The image file could not be found.", ephemeral=True)
            return None
        except OSError:
            await interaction.response.send_message("The file is not a valid image file.", ephemeral=True)
            return None

        # Create the payload
        #payload = self.create_payload(init_images=[encoded_string], resize_mode=2)

        # Build the request payload
        """{
            "resize_mode": 0,
            "show_extras_results": true,
            "gfpgan_visibility": 0,
            "codeformer_visibility": 0,
            "codeformer_weight": 0,
            "upscaling_resize": 2,
            "upscaling_resize_w": 512,
            "upscaling_resize_h": 512,
            "upscaling_crop": true,
            "upscaler_1": "None",
            "upscaler_2": "None",
            "extras_upscaler_2_visibility": 0,
            "upscale_first": false,
            "image": ""
            }"""
        payload = {
            "upscaling_resize": 4,
            "upscaler_1": "R-ESRGAN 4x+",
            "image": encoded_string,
            "upscale_first": True
        }

        # Send the request to the img2img API
        #response = await self.img2img(payload)
        # Create a session and send the request to the API
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:7860/sdapi/v1/extra-single-image", json=payload) as response:
                response_json = await response.json()
            with open('response.txt', 'w') as file:
                file.write(str(response_json))
            


        # If the response is not None, save the upscaled image
        if response is not None:
            # Get the base64 string of the upscaled image from the response
            upscaled_image_data = response_json['image']


            # Convert the base64 string back to an image
            upscaled_image = Image.open(BytesIO(base64.b64decode(upscaled_image_data)))

            # Save the upscaled image and return the path
            folder_path = "image_cache/upscaled_images"
            os.makedirs(folder_path, exist_ok=True)
            upscaled_image_path = os.path.join(folder_path, f"upscaled_image.png")
            upscaled_image.save(upscaled_image_path)

            return upscaled_image_path
        else:
            await interaction.response.send_message("Failed to upscale the image.", ephemeral=True)
            return None
        
    async def create_img2img(self, image_path, interaction):
        # Read the image file and encode it to base64
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        # Create the payload for the API request
        payload = self.create_payload(encoded_string)

        # Make the API request
        response = requests.post('http://localhost:7860/sdapi/v1/img2img', json=payload)

        if response.status_code == 200:
            # Decode the response and save the upscaled image
            response_data = response.json()
            upscaled_images_data = response_data['images']

            # Decode each image and convert it to a PIL Image object
            upscaled_images = [Image.open(BytesIO(base64.b64decode(image_data))) for image_data in upscaled_images_data]

            # Save each upscaled image in the 'image_cache' folder
            for i, image in enumerate(upscaled_images):
                upscaled_image_path = os.path.join("image_cache", f"upscaled_image_{i}.png")
                image.save(upscaled_image_path)

            return upscaled_images
        else:
            await interaction.response.send_message("Failed to generate upscaled images.", ephemeral=True)
            return None

async def setup(bot):
    await bot.add_cog(Image2Image(bot))

