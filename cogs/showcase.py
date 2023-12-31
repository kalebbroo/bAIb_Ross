from discord.ext import commands
from typing import List, Dict, Any
import discord


class Showcase(commands.Cog):
    """A Cog for the Showcase channel."""
    def __init__(self, bot: commands.Bot):
        """Initialize the Showcase Cog."""
        self.bot = bot



async def setup(bot: commands.Bot) -> None:
    """Setup function to add the Cog to the bot.
    Args:
        bot: The Discord bot.
    """
    await bot.add_cog(Showcase(bot))