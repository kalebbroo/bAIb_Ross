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
from dotenv import load_dotenv

load_dotenv()
SWARM_URL = os.getenv('SWARM_URL')

class APICalls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.address = SWARM_URL
        self.session_id = ""
        self.session = aiohttp.ClientSession()  # Create a session to reuse

    async def get_session(self):
        async with self.session.post(f"{self.address}/API/GetNewSession", json={}) as response:
            if response.status != 200:
                raise Exception(f"Failed to get session. HTTP Status Code: {response.status}, Response Content: {await response.text()}")
            self.session_id = (await response.json()).get("session_id", "")
            if not self.session_id:
                raise Exception("Failed to obtain session")
            return self.session_id

    @staticmethod
    def create_payload(session_id, prompt=None, negative_prompt=None, images=4,
                        donotsave=True, model=None, width=None, height=None,
                        cfgscale=None, steps=10, seed=-1, enableaitemplate=None, 
                        init_image=None, init_image_creativity=None):
        base_payload = {
            "session_id": session_id,
            "images": images,
            "donotsave": donotsave,
            "seed": seed,
            "prompt": prompt,
            "negativeprompt": negative_prompt,
            "model": model,
            "width": width,
            "height": height,
            "cfgscale": cfgscale,
            "steps": steps,
            "enableaitemplate": enableaitemplate,
            "init_image": init_image,
            "init_image_creativity": init_image_creativity
        }
        return {k: v for k, v in base_payload.items() if v is not None}

    async def call_collect(self, interaction, payload):
        uri = f"ws://{self.address[7:]}/API/GenerateText2ImageWS"
        image_grid_cog = self.bot.get_cog("ImageGrid")
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps(payload))
                
                prompt = payload.get("prompt", "No prompt")
                negative = payload.get("negativeprompt", "No negative prompt")
                message = await interaction.followup.send(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`')
                
                while True:
                    try:
                        response_data = await ws.recv()
                        data = json.loads(response_data)
                        
                        gen_progress = data.get('gen_progress', {})
                        preview_data = gen_progress.get('preview', None)
                        image_data = data.get('image', None)
                        error_data = data.get('error', None)

                        if preview_data:
                            base64_str = preview_data.split('data:image/jpeg;base64,')[-1]
                            image_data = base64.b64decode(base64_str)
                            image = Image.open(BytesIO(image_data))

                            embed, file = await image_grid_cog.image_grid(image, interaction, is_preview=True, payload=payload)
                            await message.edit(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`',
                                                embed=embed, attachments=[file])

                        elif error_data:
                            error_msg = f"Failed to generate image. Error: {error_data}"
                            logging.error(error_msg)
                            await interaction.followup.send(content=error_msg)
                            break

                        elif image_data:
                            base64_str = image_data.split('data:image/jpeg;base64,')[-1]
                            image = Image.open(BytesIO(base64.b64decode(base64_str)))

                            embed, file = await image_grid_cog.image_grid(image, interaction, is_preview=False, payload=payload)
                            await message.edit(content=f'Generating images for {interaction.user.mention} using\n**Prompt:** `{prompt}` \n**Negative:** `{negative}`',
                                                embed=embed, attachments=[file])

                    except websockets.exceptions.ConnectionClosedOK:
                        break
                    except Exception as e:
                        logging.error(f"An error occurred: {e}")
                        break
        except (websockets.exceptions.ConnectionClosedOK, websockets.exceptions.ConnectionClosedError):
            logging.warning("WebSocket connection closed. Attempting to reconnect...")
            new_session_id = await self.get_session()
            payload["session_id"] = new_session_id
            await self.call_collect(interaction, payload)
        except Exception as e:
            logging.error(f"An error occurred: {e}")


async def setup(bot):
    await bot.add_cog(APICalls(bot))
