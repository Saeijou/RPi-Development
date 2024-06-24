import discord
from discord.ext import commands
import os

class CogManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, cog: str):
        try:
            await self.bot.load_extension(f'cogs.{cog}')
            await ctx.send(f'Cog `{cog}` has been loaded.')
        except Exception as e:
            await ctx.send(f'Failed to load cog `{cog}`. Error: {str(e)}')

    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx, cog: str):
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
            await ctx.send(f'Cog `{cog}` has been unloaded.')
        except Exception as e:
            await ctx.send(f'Failed to unload cog `{cog}`. Error: {str(e)}')

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, cog: str):
        try:
            await self.bot.reload_extension(f'cogs.{cog}')
            await ctx.send(f'Cog `{cog}` has been reloaded.')
        except Exception as e:
            await ctx.send(f'Failed to reload cog `{cog}`. Error: {str(e)}')

    @commands.command()
    @commands.is_owner()
    async def list_cogs(self, ctx):
        cogs = [f[:-3] for f in os.listdir('./cogs') if f.endswith('.py')]
        loaded_cogs = [ext.split('.')[-1] for ext in self.bot.extensions]
        cog_list = [f"{cog} ({'Loaded' if cog in loaded_cogs else 'Unloaded'})" for cog in cogs]
        await ctx.send("Available cogs:\n" + "\n".join(cog_list))

async def setup(bot):
    await bot.add_cog(CogManager(bot))