# add code so the user can use Chat GPT to give them a better prompt
from discord.ext import commands
from discord import app_commands



class GPT(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GPT(bot))