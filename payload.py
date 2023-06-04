import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select, Modal, TextInput
import openai
from config import GPT_KEY
from typing import Optional, List, Dict, Any

class Payload:
    def __init__(self, bot):
        self.bot = bot


    # Create the payload
    async def create_payload(self, prompt: str, negative_prompt: Optional[str] = None,
                            model_name: Optional[str] = None,
                            guidance_scale: Optional[str] = None, sampler: Optional[str] = None,
                            styles: Optional[str] = None,
                            extra_net: Optional[str] = None, facefix: Optional[bool] = None,
                            highres_fix: Optional[bool] = None, clip_skip: Optional[int] = None,
                            strength: Optional[float] = None, init_image: Optional[discord.Attachment] = None,
                            batch: Optional[int] = None, encoded_string: Optional[str] = None):
        # Define the base payload
        safe_negative = "nsfw, explicit, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"
        if negative_prompt is None or negative_prompt.lower() == "nsfw":
            negative_prompt = safe_negative

        base_payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": 10,
            "seed": -1,
            "cfg_scale": 0.7,
            "sampler_name": "DPM++ 2S a Karras",
        }

        # Define the additional payloads
        text2img_payload = {
            "width": 512,
            "height": 512,
            "enable_hr": highres_fix,
            "restore_faces": facefix,
            "batch_size": 4,
            "model_name": model_name
        }

        img2img_payload = {
            "init_images": init_image,
            "denoising_strength": strength,
            "batch_size": batch,
            "width": 512,
            "height": 512,
        }

        upscale_payload = {
            "upscaling_resize": 4,
            "upscaler_1": "R-ESRGAN 4x+",
            "image": encoded_string,
            "upscale_first": True
        }
        payload = base_payload.copy()  # Create a copy of the base payload

        # Update the payload with the additional payloads
        if model_name is not None:
            payload.update(text2img_payload)

        elif init_image is not None:
            payload.update(img2img_payload)

        elif encoded_string is not None:
            payload.update(upscale_payload)

        # Remove the None values from the payload
        payload = await self.remove_none(payload)

        return payload
    
    @staticmethod
    async def remove_none(payload):
        return {k: v for k, v in payload.items() if v is not None}
        
