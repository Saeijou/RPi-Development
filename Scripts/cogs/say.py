import discord
from discord.ext import commands


class SayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.dm_only()
    @commands.command(name="say")
    async def say(self, ctx, channel_id: int, *, phrase: str):
        try:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                await ctx.send("Invalid channel ID. Please provide a valid channel ID.")
                return

            if not isinstance(channel, discord.TextChannel):
                await ctx.send("The provided ID does not correspond to a text channel.")
                return

            await channel.send(phrase)
            await ctx.send(f"Message sent to channel {channel.name} (ID: {channel.id})")
        except discord.Forbidden:
            await ctx.send("I don't have permission to send messages in that channel.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(SayCog(bot))