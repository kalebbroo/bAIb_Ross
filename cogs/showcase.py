from discord.ext import commands
import discord

class Showcase(commands.Cog):
    """A Cog for the Showcase channel."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.votes = {}  # To store votes for each message

    class VotingSelect(discord.ui.Select):
        def __init__(self, showcase_cog, message_id):
            self.showcase_cog = showcase_cog
            self.message_id = message_id
            options = [
                discord.SelectOption(label="Vote Up", value="upvote", emoji="👍"),
                discord.SelectOption(label="Vote Down", value="downvote", emoji="👎"),
                discord.SelectOption(label="Report", value="report", emoji="⚠️"),
            ]
            super().__init__(placeholder="Choose an action...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            # Increment the vote count and update the embed
            self.showcase_cog.votes.setdefault(self.message_id, {"upvote": 0, "downvote": 0, "report": 0})
            self.showcase_cog.votes[self.message_id][self.values[0]] += 1

            message = await interaction.channel.fetch_message(self.message_id)
            embed = message.embeds[0]
            embed.clear_fields()
            embed.add_field(name="Upvotes", value=self.showcase_cog.votes[self.message_id]["upvote"], inline=True)
            embed.add_field(name="Downvotes", value=self.showcase_cog.votes[self.message_id]["downvote"], inline=True)
            await message.edit(embed=embed)

            # Send a response to the user
            vote_response = "upvoted!" if self.values[0] == "upvote" else "downvoted!" if self.values[0] == "downvote" else "reported!"
            await interaction.response.send_message(f"You have {vote_response}", ephemeral=True)

    async def showcase_image(self, guild: discord.Guild, image_url: str, user: discord.User):
        """Showcase an image in the 'Showcase' channel."""
        try:
            showcase_channel = discord.utils.get(guild.channels, name='showcase', type=discord.ChannelType.text)
            if not showcase_channel:
                print("Showcase channel not found.")
                return

            embed = discord.Embed(title="Showcase Image", description=f"Submitted by {user.display_name}")
            embed.set_image(url=image_url)

            message = await showcase_channel.send(embed=embed)
            voting_select = self.VotingSelect(self, message.id)
            view = discord.ui.View()
            view.add_item(voting_select)
            await message.edit(view=view)

        except Exception as e:
            print(f"Failed to showcase image: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Showcase(bot))