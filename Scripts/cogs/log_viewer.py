import discord
from discord.ext import commands
import os
import configparser
from io import StringIO

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

class LogViewer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_log_file = config['Paths']['bot_log_file']
        self.script_runner_log_file = config['Paths']['log_file']

    def get_last_25_lines(self, log_file):
        with open(log_file, 'r') as file:
            lines = file.readlines()
            last_25_lines = lines[-25:]
        return ''.join(last_25_lines)

    @commands.command(name="botlog")
    @commands.is_owner()
    async def view_bot_log(self, ctx):
        """View the last 25 lines of bot.log"""
        logs = self.get_last_25_lines(self.bot_log_file)
       
        if len(logs) > 2000:
            # If the log is too long, send it as a file
            buffer = StringIO(logs)
            file = discord.File(buffer, filename="bot_last_25_lines.log")
            await ctx.send("Here are the last 25 lines of bot logs:", file=file)
        else:
            await ctx.send(f"```\n{logs}\n```")

    @commands.command(name="scriptlog")
    @commands.is_owner()
    async def view_script_runner_log(self, ctx):
        """View the last 25 lines of script_runner.log"""
        logs = self.get_last_25_lines(self.script_runner_log_file)
       
        if len(logs) > 2000:
            # If the log is too long, send it as a file
            buffer = StringIO(logs)
            file = discord.File(buffer, filename="script_runner_last_25_lines.log")
            await ctx.send("Here are the last 25 lines of script runner logs:", file=file)
        else:
            await ctx.send(f"```\n{logs}\n```")

    @commands.command(name="rmbot")
    @commands.is_owner()
    async def clear_bot_log(self, ctx):
        """Clear the bot.log file"""
        try:
            open(self.bot_log_file, 'w').close()
            await ctx.send("Bot log has been cleared.")
        except Exception as e:
            await ctx.send(f"An error occurred while clearing the bot log: {str(e)}")

    @commands.command(name="rmscript")
    @commands.is_owner()
    async def clear_script_log(self, ctx):
        """Clear the script_runner.log file"""
        try:
            open(self.script_runner_log_file, 'w').close()
            await ctx.send("Script runner log has been cleared.")
        except Exception as e:
            await ctx.send(f"An error occurred while clearing the script runner log: {str(e)}")

async def setup(bot):
    await bot.add_cog(LogViewer(bot))