import discord
from discord.ext import commands

class BotCapabilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="bothelp")
    async def display_help(self, ctx):
        embed = discord.Embed(
            title="Bot Capabilities",
            description="Here's what I can do:",
            color=discord.Color.blue()
        )

        command_list = [
            ("!ai [phrase]", "Ask Claude AI a question or give it a task. Only authorized users can use this command."),
            ("!aistats", "View your total AI usage statistics, including token count and estimated cost. Only authorized users can use this command."),
            ("!bothelp", "Display this help message showing all available commands.")
        ]

        for command, description in command_list:
            embed.add_field(name=command, value=description, inline=False)

        embed.set_footer(text="Note: Some commands are restricted to authorized users only.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotCapabilities(bot))
