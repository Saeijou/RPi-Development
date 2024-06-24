import discord
from discord.ext import commands

class BotCapabilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="bothelp")
    async def display_help(self, ctx):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blue()
        )

        command_list = [
            ("!bothelp", "Display this help message showing all available commands."),
            ("!ai [phrase]", "Ask Claude AI a question or give it a task. (Authorized users only)"),
            ("!aistats", "View your total AI usage statistics. (Authorized users only)"),
            ("!google [query]", "Search Google and return top 3 results."),
            ("!image [query]", "Search for an image on Google and return the first result."),
            ("!joke", "Tell a random joke."),
            ("!load [cog]", "Load a specific cog. (Bot owner only)"),
            ("!unload [cog]", "Unload a specific cog. (Bot owner only)"),
            ("!reload [cog]", "Reload a specific cog. (Bot owner only)"),
            ("!list_cogs", "List all available cogs and their status. (Bot owner only)"),
            ("!botlog", "View the last 24 hours of bot.log entries. (Bot owner only)"),
            ("!scriptlog", "View the last 24 hours of script_runner.log entries. (Bot owner only)")
        ]

        for command, description in command_list:
            embed.add_field(name=command, value=description, inline=False)

        embed.set_footer(text="Note: Some commands are restricted to authorized users or the bot owner only.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotCapabilities(bot))