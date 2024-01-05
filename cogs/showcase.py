from discord.ext import commands
import discord

class Showcase(commands.Cog):
    """A Cog for the Showcase channel."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class VotingButtons(discord.ui.View):
        def __init__(self, showcase_cog, message_id):
            super().__init__(timeout=None)
            self.showcase_cog = showcase_cog
            self.message_id = message_id

        @discord.ui.button(label="Vote", style=discord.ButtonStyle.success, emoji="👍")
        async def vote_up(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.process_vote(interaction, "upvote")

        @discord.ui.button(label="Vote", style=discord.ButtonStyle.danger, emoji="👎")
        async def vote_down(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.process_vote(interaction, "downvote")

        @discord.ui.button(label="Report", style=discord.ButtonStyle.secondary, emoji="⚠️", custom_id="report")
        async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            await self.process_vote(interaction, "report")
            # Disable the report button
            button.disabled = True
            # Update the message with the new view
            await interaction.message.edit(view=self)
            # Notify Admins
            for member in interaction.guild.members:
                if discord.utils.get(member.roles, name="Admin"):
                    try:
                        await member.send(f"**User:** {interaction.user.display_name} reported an image in showcase. {interaction.message.jump_url}")
                    except discord.errors.Forbidden:
                        pass  # Member has DMs off or bot cannot send DMs to them

        @discord.ui.button(label="", style=discord.ButtonStyle.secondary, emoji="🗑️", custom_id="delete")
        async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            # Get the user display name from the description of the embed
            user_name = interaction.message.embeds[0].description.split()[-1]
            # Check if the user is the author of the message
            if interaction.user.display_name != user_name:
                await interaction.followup.send("You cannot delete someone else's showcase image", ephemeral=True)
                return
            # Delete the message
            await interaction.followup.send("Your showcase has been deleted", ephemeral=True)
            await interaction.message.delete()

        async def process_vote(self, interaction: discord.Interaction, vote_type: str):
            user_name = interaction.user.name
            message = await interaction.channel.fetch_message(self.message_id)
            embed = message.embeds[0]

            # Extracting voter names from embed fields
            upvotes = embed.fields[0].value.split('\n') if embed.fields else []
            downvotes = embed.fields[1].value.split('\n') if len(embed.fields) > 1 else []

            # Removing user's previous vote if exists
            upvotes = [name for name in upvotes if name != user_name and name != "None"]
            downvotes = [name for name in downvotes if name != user_name and name != "None"]

            # Adding new vote
            match vote_type:
                case "upvote":
                    upvotes.append(user_name)
                    response_message = "You voted for this image to be the next server icon! If this was a mistake you can change your vote by clicking the downvote button"
                case "downvote":
                    downvotes.append(user_name)
                    response_message = "You voted for this image to NOT be the next server icon! If this was a mistake you can change your vote by clicking the upvote button"
                case "report":
                    await interaction.followup.send(f"Reported to admins. Just remember, snitches get stitches.", ephemeral=True)
                    return  # Don't update the embed

            # Updating the embed with new votes
            embed.clear_fields()
            embed.add_field(name="Upvotes", value="\n".join(upvotes) if upvotes else "None", inline=True)
            embed.add_field(name="Downvotes", value="\n".join(downvotes) if downvotes else "None", inline=True)

            # Calculate total vote count
            total_votes = len(upvotes) - len(downvotes)
            embed.set_footer(text=f"Total Votes: {total_votes}")

            await message.edit(embed=embed)
            await interaction.response.send_message(response_message, ephemeral=True)

    async def showcase_image(self, guild: discord.Guild, image_url: str, user: discord.User):
        try:
            showcase_channel = discord.utils.get(guild.channels, name='showcase', type=discord.ChannelType.text)
            if not showcase_channel:
                print("Showcase channel not found.")
                return

            embed = discord.Embed(title="Showcase Image", description=f"Submitted by {user.display_name}")
            embed.set_image(url=image_url)
            embed.set_thumbnail(url=user.avatar.url)
            embed.add_field(name="Upvotes", value="None", inline=True)
            embed.add_field(name="Downvotes", value="None", inline=True)
            embed.set_footer(text="Total Votes: 0")

            message = await showcase_channel.send(embed=embed)
            voting_buttons = self.VotingButtons(self, message.id)
            await message.edit(view=voting_buttons)
            # Start a new thread for the image
            await message.create_thread(name="Discussion the image")

        except Exception as e:
            print(f"Failed to showcase image: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Showcase(bot))