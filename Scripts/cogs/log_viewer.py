import discord
from discord.ext import commands
import datetime
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

    def get_last_24h_logs(self, log_file):
        current_time = datetime.datetime.now()
        yesterday = current_time - datetime.timedelta(days=1)
        
        logs = []
        with open(log_file, 'r') as file:
            for line in file:
                try:
                    log_time = datetime.datetime.strptime(line.split(':')[0], '%Y-%m-%d %H-%M-%S')
                    if log_time >= yesterday:
                        logs.append(line.strip())
                except ValueError:
                    # If we can't parse the timestamp, we'll skip this line
                    continue
        
        return '\n'.join(logs)

    @commands.command(name="botlog")
    @commands.is_owner()
    async def view_bot_log(self, ctx):
        """View the last 24 hours of bot.log"""
        logs = self.get_last_24h_logs(self.bot_log_file)
        
        if len(logs) > 2000:
            # If the log is too long, send it as a file
            buffer = StringIO(logs)
            file = discord.File(buffer, filename="bot_last_24h.log")
            await ctx.send("Here are the last 24 hours of bot logs:", file=file)
        else:
            await ctx.send(f"```\n{logs}\n```")

    @commands.command(name="scriptlog")
    @commands.is_owner()
    async def view_script_runner_log(self, ctx):
        """View the last 24 hours of script_runner.log"""
        logs = self.get_last_24h_logs(self.script_runner_log_file)
        
        if len(logs) > 2000:
            # If the log is too long, send it as a file
            buffer = StringIO(logs)
            file = discord.File(buffer, filename="script_runner_last_24h.log")
            await ctx.send("Here are the last 24 hours of script runner logs:", file=file)
        else:
            await ctx.send(f"```\n{logs}\n```")

async def setup(bot):
    await bot.add_cog(LogViewer(bot))