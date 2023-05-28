from discord.ext import commands

class Img2Img(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(self) -> None:
    await self.bot.add_cog(Img2Img(self.bot))

