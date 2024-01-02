from typing import Any, Dict, Optional
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from discord.ext import commands
import websockets
import traceback
import json
import base64
from PIL import Image
from io import BytesIO
from typing import List, Dict, Any
import discord
import logging
import aiohttp
import os
import re

SWARM_URL = os.getenv('SWARM_URL')  # Get the SWARM URL from the environment variables

class APICalls(commands.Cog):
    """A Cog for making API calls related to image generation."""
    def __init__(self, bot: commands.Bot):
        """Initialize the API Calls Cog."""
        self.bot = bot
        self.address = SWARM_URL
        self.session_id = ""
        self.session = aiohttp.ClientSession()  # Create a reusable session for API calls
        self.message_data: Dict[int, Dict[str, Any]] = {}  # Message info, indexed by message ID. To be referenced by buttons


    async def get_session(self) -> str:
        """Get a new session ID from the API.
        Returns:
            The new session ID.
        """
        async with self.session.post(f"{self.address}/API/GetNewSession", json={}) as response:
            if response.status != 200:
                raise Exception(f"Failed to get session. HTTP Status Code: {response.status}, Response Content: {await response.text()}")
            self.session_id = (await response.json()).get("session_id", "")
            if not self.session_id:
                raise Exception("Failed to obtain session")
            return self.session_id

    @staticmethod
    def create_payload(session_id: str, prompt: Optional[str] = "Photorealistic, 4k, ultra high definition, portrait", 
                       negativeprompt: Optional[str] = "NSFW, low quality, blurry, low resolution, nipples, extra limbs",
                    images: int = 1, batchsize: Optional[int] = 4, donotsave: bool = True, model: str = "juggernautXL_version6Rundiffusion.safetensors", 
                    width: int = 1024, height: int = 1024, cfgscale: int = 9, upscale: Optional[bool] = False,
                    steps: int = 28, seed: int = -1, enableaitemplate: Optional[Any] = None, 
                    init_image: Optional[str] = None, init_image_creativity: Optional[float] = None,
                    lora: Optional[str] = None, embedding: Optional[str] = None, 
                    video_format: Optional[str] = None, video_frames: Optional[int] = None, 
                    video_fps: Optional[int] = None, video_steps: Optional[int] = None, 
                    video_cfg: Optional[float] = None, video_min_cfg: Optional[float] = None, 
                    video_motion_bucket: Optional[int] = None, sampler: Optional[str] = None, 
                    scheduler: Optional[str] = None, aspect_ratio: Optional[str] = None, 
                    video_model: Optional[str] = None) -> Dict:
        """Create a payload for an API call.
        Args:
            session_id: The session ID for the API call.
            prompt: The text prompt.
            negativeprompt: The negative text prompt.
            images: The number of images to generate.
            donotsave: Whether to save the images or not.
            model: The model to use for generation.
            width: The width of the images.
            height: The height of the images.
            cfgscale: The configuration scale.
            steps: The number of steps to generate.
            seed: The seed for randomization.
            enableaitemplate: Enable AI template (if any).
            init_image: The initial image (if any).
            init_image_creativity: The creativity level for the initial image.
            lora: The LORA setting (if any).
            embedding: The embedding (if any).
            sampler: The sampling method for the video.
            scheduler: The scheduling method for the video.
            aspect_ratio: The aspect ratio of the video.
            video_model: The specific model used for video generation.
            video_format: The format of the video.
            video_frames: The number of frames in the video.
            video_fps: The frames per second of the video.
            video_steps: The number of steps for the video.
            video_cfg: The configuration for the video.
            video_min_cfg: The minimum configuration for the video.
            video_motion_bucket: The motion bucket for the video.
        Returns:
            The created payload.
        """
        base_payload = {
                "session_id": session_id,
                "images": images,
                "batchsize": batchsize,
                "donotsave": donotsave,
                "seed": seed,
                "prompt": prompt,
                "negativeprompt": negativeprompt,
                "model": model,
                "width": width,
                "height": height,
                "cfgscale": cfgscale,
                "steps": steps,
                "enableaitemplate": enableaitemplate,
                "init_image": init_image,
                "init_image_creativity": init_image_creativity,
                "upscale": upscale,
                "lora": lora,
                "embedding": embedding,
                "sampler": sampler,
                "scheduler": scheduler,
                "aspect_ratio": aspect_ratio,
                # Video-specific parameters
                "video_model": video_model,
                "video_format": video_format,
                "video_frames": video_frames,
                "video_fps": video_fps,
                "video_steps": video_steps,
                "video_cfg": video_cfg,
                "video_min_cfg": video_min_cfg,
                "video_motion_bucket": video_motion_bucket,
            }
        return {k: v for k, v in base_payload.items() if v is not None}

    async def call_collect(self, interaction: discord.Interaction, payload: Dict) -> None:
        """Call the API and collect the generated images.
        Args:
            interaction: The Discord interaction that triggered this.
            payload: The payload for the API call.
        """
        #await APICalls.save_models_and_loras_to_files(self)
        upscale = payload.get('upscale', False)
        # Send a placeholder follow-up message
        model_name = payload.get('model', 'Unknown')
        width = payload.get('width', 'Unknown')
        height = payload.get('height', 'Unknown')
        seed = payload.get('seed', 'Unknown')
        images = payload.get('images', 'Unknown')
        steps = payload.get('steps', 'Unknown')
        cfgscale = payload.get('cfgscale', 'Unknown')
        prompt = payload.get("prompt", "No prompt")
        negative = payload.get("negativeprompt", "No negative prompt")
        placeholder_embed = discord.Embed(description="Generating image, one moment please...", color=discord.Color.blue())
        placeholder_embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.avatar.url)
        placeholder = await interaction.followup.send(embed=placeholder_embed, wait=True)

        if upscale:
            await APICalls.aiohttp_call_collect(self, interaction, payload)
            return

        uri = f"ws://{self.address[7:]}/API/GenerateText2ImageWS"  # WebSocket URI for the API
        image_grid_cog = self.bot.get_cog("ImageGrid")  # Get the ImageGrid Cog

        try:
            async with websockets.connect(uri, ping_interval=18000, ping_timeout=18100, max_size=2**30) as ws:
                await ws.send(json.dumps(payload))
                #print(ws.max_size)
                new_embed = discord.Embed(title=f'Generating images for {interaction.user.display_name}', 
                                          description=f'using `{model_name}`\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`', 
                                          color=discord.Color.blue())
                footer_txt = f"Width: {width} | Height: {height} | Seed: {seed} | Steps: {steps} | CFG Scale: {cfgscale}"
                new_embed.set_footer(text=footer_txt, icon_url=interaction.user.avatar.url)
                new_embed.set_author(name=interaction.client.user.display_name, icon_url=interaction.client.user.avatar.url)
    
                message = await placeholder.edit(embed=new_embed)
                
                while True:
                    try:
                        response_data = await ws.recv()
                        data = json.loads(response_data)
                        
                        gen_progress = data.get('gen_progress', {})
                        preview_data = gen_progress.get('preview', None)
                        image_data = data.get('image', None)
                        error_data = data.get('error', None)

                        if preview_data or image_data:
                            base64_str = (preview_data or image_data).split('data:image/jpeg;base64,')[-1]
                            image = Image.open(BytesIO(base64.b64decode(base64_str)))
                            is_preview = bool(preview_data)

                            print(f"Processing {'preview' if is_preview else 'final'} image")

                            await image_grid_cog.process_image(interaction, image, is_preview, message, payload)

                        elif error_data:
                            error_msg = f"Failed to generate image. Error: {error_data}"
                            logging.error(error_msg)
                            await interaction.followup.send(content=error_msg)
                            break

                    except websockets.exceptions.ConnectionClosedOK:
                        print("Connection closed OK")
                        break
                    except Exception as e:
                        full_traceback = traceback.format_exc()
                        logging.error(f"An error occurred: {e}\nFull Traceback: {full_traceback}")
                        print(f"An exception occurred: {e}\nFull Traceback: {full_traceback}")
                        break

        except (websockets.exceptions.ConnectionClosedOK, websockets.exceptions.ConnectionClosedError):
            print("Connection closed unexpectedly. Reconnecting...")
            logging.warning("WebSocket connection closed. Attempting to reconnect...")
            new_session_id = await self.get_session()
            payload["session_id"] = new_session_id
            await self.call_collect(interaction, payload)
        except Exception as e:
            full_traceback = traceback.format_exc()
            logging.error(f"An error occurred: {e}\nFull Traceback: {full_traceback}")
            print(f"An exception occurred: {e}\nFull Traceback: {full_traceback}")
            
    async def save_models_and_loras_to_files(self):
        """Fetch and save models and LoRAs lists to separate text files, excluding the 'preview_image' key."""
        # Fetch models and LoRAs lists
        models_list = await self.get_models('model')
        loras_list = await self.get_models('LoRA')

        # Remove the 'preview_image' key from each entry in the lists
        for entry in models_list + loras_list:
            entry.pop('preview_image', None)  # Safely remove the key if it exists

        # Convert the lists to JSON strings
        models_json = json.dumps(models_list, indent=4)
        loras_json = json.dumps(loras_list, indent=4)

        # Save to text files
        with open('models_list.txt', 'w', encoding='utf-8') as models_file:
            models_file.write(models_json)

        with open('loras_list.txt', 'w', encoding='utf-8') as loras_file:
            loras_file.write(loras_json)

        print("Models and LoRAs have been saved to text files without preview images.")


    async def get_models(self, model_type: str = "model") -> List[Dict[str, Any]]:
        """Fetch the list of available models or LoRAs from the API.
        Args:
            model_type (str): The type of items to fetch ('model' or 'LoRA').
        Returns:
            A list of dictionaries containing item information.
        """
        url = f"{SWARM_URL}/API/ListModels"
        api_cog = self.bot.get_cog("APICalls")
        session_id = await api_cog.get_session()

        params = {
            "path": "",
            "depth": 2 if model_type == "model" else 1,
            "session_id": session_id
        }
        if model_type == "LoRA":
            params["subtype"] = "LoRA"

        async with api_cog.session.post(url, json=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to get {model_type} list. HTTP Status Code: {response.status}, Response Content: {await response.text()}")
            data = await response.json()
            models_list = [
                {
                    "title": file.get("title"),
                    "name": file.get("name"),
                    "standard_width": file.get("standard_width"),
                    "standard_height": file.get("standard_height"),
                    "description": file.get("description"),
                    "preview_image": file.get("preview_image"),
                    "trigger_phrase": file.get("trigger_phrase"),
                    "usage_hint": file.get("usage_hint"),
                }
                for file in data.get("files", [])
            ]
            # Additional logic for sorting models (not needed for LoRAs)
            if model_type == "model":
                models_list.sort(key=lambda x: int(x['title'].split()[0].replace('.', '')))

            print(f"{model_type.title()} list contains {len(models_list)} {model_type}")

            return models_list
        
    async def aiohttp_call_collect(self, interaction: discord.Interaction, payload: Dict) -> None:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.address}/API/GenerateText2Image", json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        images = data.get('images', [])
                        for image_data in images:
                            content_type = re.search(r'data:(image\/\w+);base64,', image_data)
                            file_extension = "png" if not content_type else content_type.group(1).split('/')[-1]
                            image_bytes = base64.b64decode(re.sub(r'^data:image\/\w+;base64,', '', image_data))
                            with BytesIO(image_bytes) as image_file:
                                image_file.seek(0)
                                file = discord.File(fp=image_file, filename=f"generated_image.{file_extension}")
                                embed = discord.Embed(title="Generated Image", color=discord.Color.green())
                                embed.set_image(url=f"attachment://{file.filename}")
                                embed.set_footer(text=f"Requested by {interaction.user.display_name}", 
                                                 icon_url=interaction.user.avatar.url)
                                # Add additional fields for the image details
                                embed.add_field(name="Prompt", value=payload.get("prompt", "No prompt"), inline=False)
                                embed.add_field(name="Negative Prompt", value=payload.get("negativeprompt", 
                                                                                          "No negative prompt"), inline=False)
                                embed.add_field(name="Model", value=payload.get("model", "Unknown"), inline=True)
                                embed.add_field(name="Width", value=payload.get("width", "Unknown"), inline=True)
                                embed.add_field(name="Height", value=payload.get("height", "Unknown"), inline=True)
                                embed.add_field(name="Steps", value=payload.get("steps", "Unknown"), inline=True)
                                embed.add_field(name="CFG Scale", value=payload.get("cfgscale", "Unknown"), inline=True)
                                await interaction.followup.send(embed=embed, file=file)
                    else:
                        error_message = f"API call failed with status code: {response.status}"
                        await interaction.followup.send(error_message)
            except Exception as e:
                await interaction.followup.send(f"An error occurred during the API call: {e}")


async def setup(bot: commands.Bot) -> None:
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(APICalls(bot))
