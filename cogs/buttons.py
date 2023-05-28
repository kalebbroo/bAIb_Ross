from cogs.text2image import text2image
from discord.ext import commands
from discord import ButtonStyle, Interaction
from discord.ui import Button, View
import asyncio

class Buttons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class ImageView(View):
        def __init__(self, ctx, image_urls, settings):
            super().__init__()
            self.ctx = ctx
            self.image_urls = image_urls
            self.settings = settings

            # Add buttons to the view with custom ids
            self.add_item(Button(style=ButtonStyle.secondary, label="Choose img", custom_id="choose_img"))
            self.add_item(Button(style=ButtonStyle.primary, label="Upscale", custom_id="upscale"))
            self.add_item(Button(style=ButtonStyle.primary, label="Regenerate", custom_id="regenerate"))
            self.add_item(Button(style=ButtonStyle.danger, label="Delete", custom_id="delete"))
            self.add_item(Button(style=ButtonStyle.secondary, label="Edit Prompt", custom_id="edit_prompt"))
            self.add_item(Button(style=ButtonStyle.secondary, label="Randomize Seed", custom_id="randomize_seed"))
            self.add_item(Button(style=ButtonStyle.secondary, label="View Info", custom_id="view_info"))

        async def choose_img(self, interaction: Interaction, button: Button):
            # Here you would implement the logic for choosing one of the images for img2img
            pass

        async def upscale(self, interaction: Interaction, button: Button):
            # Here you would implement the logic for upscaling and saving the image
            pass

        async def regenerate(self, interaction: Interaction, button: Button):
            # Regenerate the image using the stored settings
            new_image = text2image(**self.settings)
            # Update the message with the new image
            await self.ctx.message.edit(content=new_image)

        async def delete(self, interaction: Interaction, button: Button):
            # Delete the message
            await self.ctx.message.delete()

        async def edit_prompt(self, interaction: Interaction, button: Button):
            # Here you would implement the logic for editing the prompt
            pass

        async def randomize_seed(self, interaction: Interaction, button: Button):
            # Here you would implement the logic for randomizing the seed
            pass

        async def view_info(self, interaction: Interaction, button: Button):
            # Here you would implement the logic for viewing the image's information
            pass

    async def create_view(self, ctx, image_urls, settings):
        # Create the view and add it to the message
        view = self.ImageView(ctx, image_urls, settings)
        await ctx.message.edit(view=view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        match interaction.data["custom_id"]:
            case "choose_img":
                await interaction.view.choose_img(interaction)
            case "upscale":
                await interaction.view.upscale(interaction)
            case "regenerate":
                await interaction.view.regenerate(interaction)
            case "delete":
                await interaction.view.delete(interaction)
            case "edit_prompt":
                await interaction.view.edit_prompt(interaction)
            case "randomize_seed":
                await interaction.view.randomize_seed(interaction)
            case "view_info":
                await interaction.view.view_info(interaction)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Buttons(bot))