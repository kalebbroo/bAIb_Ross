from typing import Any, Dict, Optional
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from discord.ext import commands
import websockets
import json
import base64
from PIL import Image
from io import BytesIO
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
        self.image_paths: Dict[str, str] = {}  # To store image paths, indexed by user ID. Used for button logic.


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
                       images: int = 4, donotsave: bool = True, model: str = "OfficialStableDiffusion/sd_xl_base_1.0.safetensors", 
                       width: int = 512, height: int = 512, cfgscale: int = 7,
                       steps: int = 20, seed: int = -1, enableaitemplate: Optional[Any] = None, 
                       init_image: Optional[str] = None, init_image_creativity: Optional[float] = None, 
                       lora: Optional[str] = None, embedding: Optional[str] = None) -> Dict:
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
            "lora": lora,
            "embedding": embedding,
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
            async with websockets.connect(uri, ping_interval=120, ping_timeout=210) as ws:
                await ws.send(json.dumps(payload))
                #print("Sent payload to WebSocket")
                
                prompt = payload.get("prompt", "No prompt")
                negative = payload.get("negativeprompt", "No negative prompt")
                message = await interaction.followup.send(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`')
                
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

                            embed, file = await image_grid_cog.image_grid(image, interaction, is_preview=True, payload=payload)
                            await message.edit(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`',
                                                embed=embed, attachments=[file])
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

                            embed, file = await image_grid_cog.image_grid(image, interaction, is_preview=False, payload=payload)

                            # Create an instance of the ImageButtons view from the Buttons Cog
                            buttons_view = self.bot.get_cog('Buttons').ImageButtons(self.bot, interaction, payload)
                            await message.edit(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`',
                                                embed=embed, attachments=[file], view=buttons_view)

                    except websockets.exceptions.ConnectionClosedOK:
                        print("Connection closed OK")
                        break
                    except Exception as e:
                        logging.error(f"An error occurred: {e}")
                        print(f"An exception occurred: {e}")
                        break

        except (ConnectionClosedOK, ConnectionClosedError):
            print("Connection closed unexpectedly. Reconnecting...")
            # Handle connection issues
            logging.warning("WebSocket connection closed. Attempting to reconnect...")
            new_session_id = await self.get_session()
            payload["session_id"] = new_session_id
            await self.call_collect(interaction, payload)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            print(f"An exception occurred: {e}")

async def setup(bot: commands.Bot) -> None:
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(APICalls(bot))
