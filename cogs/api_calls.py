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
    def create_payload(session_id: str, prompt: Optional[str] = None, negativeprompt: Optional[str] = None, 
                    images: int = 4, donotsave: bool = True, model: str = "turbovisionxlSuperFastXLBasedOnNew_alphaV0101Bakedvae.safetensors", 
                    width: int = 768, height: int = 1344, cfgscale: int = 2.5, upscale: Optional[bool] = False,
                    steps: int = 8, seed: int = -1, enableaitemplate: Optional[Any] = None, 
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
        #print(f"Payload: {payload}")  # Debugging line
        uri = f"ws://{self.address[7:]}/API/GenerateText2ImageWS"  # WebSocket URI for the API
        image_grid_cog = self.bot.get_cog("ImageGrid")  # Get the ImageGrid Cog

        # Handling WebSocket connection and image generation
        try:
            async with websockets.connect(uri, ping_interval=1800, ping_timeout=1810, max_size=2**21) as ws:
                await ws.send(json.dumps(payload))
                print(ws.max_size)
                #print("Sent payload to WebSocket")
                
                prompt = payload.get("prompt", "No prompt")
                negative = payload.get("negativeprompt", "No negative prompt")
                message = await interaction.followup.send(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`')
                message_id = message.id 
                print(f"Message ID call_collect: {message_id}")
                
                while True:
                    try:
                        response_data = await ws.recv()
                        #print(f"Received data: {response_data}")
                        data = json.loads(response_data)
                        
                        gen_progress = data.get('gen_progress', {})
                        preview_data = gen_progress.get('preview', None)
                        image_data = data.get('image', None)
                        error_data = data.get('error', None)

                        # Handle different types of data received from the WebSocket
                        if preview_data:
                            #print("Processing preview data...")
                            # Process preview image data
                            base64_str = preview_data.split('data:image/jpeg;base64,')[-1]
                            image_data = base64.b64decode(base64_str)
                            image = Image.open(BytesIO(image_data))

                            embed, file = await image_grid_cog.image_grid(image, interaction, is_preview=True, payload=payload, message_id=message_id)
                            await message.edit(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`',
                                                embed=embed, attachments=[file])
                            image_grid_cog = self.bot.get_cog("ImageGrid")
                        elif error_data:
                            print(f"Received error data: {error_data}")
                            # Log error and send error message
                            error_msg = f"Failed to generate image. Error: {error_data}"
                            logging.error(error_msg)
                            await interaction.followup.send(content=error_msg)
                            break

                        elif image_data:
                            print("Processing image data...")
                            # Process final image data
                            base64_str = image_data.split('data:image/jpeg;base64,')[-1]
                            image = Image.open(BytesIO(base64.b64decode(base64_str)))

                            embed, file = await image_grid_cog.image_grid(image, interaction, is_preview=False, payload=payload, message_id=message_id)

                            # Check if it's the last image in the last grid
                            if image_grid_cog.current_quadrant == 4:  
                                buttons_view = self.bot.get_cog('Buttons').ImageButtons(self.bot, interaction, payload, message_id=message_id)
                                await message.edit(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`',
                                                    embed=embed, attachments=[file], view=buttons_view)
                            else:
                                await message.edit(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`',
                                                    embed=embed, attachments=[file])
                            # Store information in the dictionary
                            if message_id not in self.message_data:
                                self.message_data[message_id] = {'payload': payload, 'user_id': interaction.user.id, 'image_files': []}

                    except websockets.exceptions.ConnectionClosedOK:
                        print("Connection closed OK")
                        break
                    except Exception as e:
                        full_traceback = traceback.format_exc()
                        logging.error(f"An error occurred: {e}\nFull Traceback: {full_traceback}")
                        print(f"An exception occurred: {e}\nFull Traceback: {full_traceback}")
                        break

        except (ConnectionClosedOK, ConnectionClosedError):
            print("Connection closed unexpectedly. Reconnecting...")
            # Handle connection issues
            logging.warning("WebSocket connection closed. Attempting to reconnect...")
            new_session_id = await self.get_session()
            payload["session_id"] = new_session_id
            await self.call_collect(interaction, payload)
        except Exception as e:
            full_traceback = traceback.format_exc()
            logging.error(f"An error occurred: {e}\nFull Traceback: {full_traceback}")
            print(f"An exception occurred: {e}\nFull Traceback: {full_traceback}")

    # TODO: Remove redundant code now that its in the same cog
    async def get_model_list(self) -> List[Dict[str, Any]]:
        """Fetch the list of available models from the API.
        Returns:
            A list of dictionaries containing model information.
        """
        url = f"{SWARM_URL}/API/ListModels"
        api_cog = self.bot.get_cog("APICalls")  # Get a reference to the APICalls Cog
        session_id = await api_cog.get_session()  # Use the get_session method from APICalls Cog
        
        params = {
            "path": "",
            "depth": 2,
            "session_id": session_id
        }
        # Use the session from APICalls Cog
        async with api_cog.session.post(url, json=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to get model list. HTTP Status Code: {response.status}, Response Content: {await response.text()}")
            data = await response.json()
            model_list = [
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
            # Sort the model list by 'title'
            model_list.sort(key=lambda x: int(x['title'].split()[0].replace('.', '')))
            #titles = [model['title'] for model in model_list]
            #print(titles)
            print(f"Model list contains {len(model_list)} models")
            
            return model_list

async def setup(bot: commands.Bot) -> None:
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(APICalls(bot))
