import aiohttp
import base64
import os
from io import BytesIO
from PIL import Image
from discord.ext import commands
from payload import Payload

class Image2Image(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def img2img_payload(self, bot, interaction, init_images, prompt):
        payload_instance = Payload(bot)
        payload = await payload_instance.create_payload(prompt=prompt, negative_prompt="Your negative prompt", init_images=init_images)
        return payload


    
    async def upscale_payload(self, bot, interaction, encoded_string):
        payload_instance = Payload(bot)
        payload = await payload_instance.create_payload(prompt="Your prompt", negative_prompt="nsfw", encoded_string=encoded_string)
        return payload


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


        # Build the upscale payload
        payload = await self.upscale_payload(self.bot, interaction, encoded_string)


        # Create a session and send the request to the API
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:7860/sdapi/v1/extra-single-image", json=payload) as response:
                response_json = await response.json()
                #print(f"Response JSON: {response_json}")
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
            await interaction.followup.send("Failed to upscale the image.", ephemeral=True)
            return None
        
    async def create_img2img(self, image_path, interaction, payload):
        # Read the image file and encode it to base64
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            # Add the prefix
            encoded_string = "data:image/png;base64," + encoded_string

        # Create the payload for the API request
        prompt = payload['prompt']
        new_payload = await self.img2img_payload(self.bot, interaction, [encoded_string], prompt)


        #print(f"img2img Payload: {payload}")

        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:7860/sdapi/v1/img2img', json=new_payload) as response:
                if response.status == 200:
                    # Decode the response and save the upscaled image
                    response_data = await response.json()
                    new_images_data = response_data['images']

                    # Decode each image and convert it to a PIL Image object
                    new_images = [Image.open(BytesIO(base64.b64decode(image_data))) for image_data in new_images_data]

                    # Save each new image in the 'image_cache' folder
                    for i, image in enumerate(new_images):
                        folder_path = "image_cache/new_images"
                        os.makedirs(folder_path, exist_ok=True)
                        new_images_path = os.path.join(folder_path, f"new_images_{i}.png")
                        image.save(new_images_path)

                    return new_images
                else:
                    await interaction.followup.send("Failed to generate images.", ephemeral=True)
                    return None
                

async def setup(bot):
    await bot.add_cog(Image2Image(bot))