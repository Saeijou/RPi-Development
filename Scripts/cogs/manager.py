import discord
from discord.ext import commands
import os
import logging
import asyncio
from typing import Optional
import configparser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

class CogManager(commands.Cog):
    """A cog for managing other cogs (loading, unloading, reloading)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cogs_dir = config['Paths']['cogs_folder']

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Check if the user is the bot owner before allowing use of any command in this cog."""
        return await self.bot.is_owner(ctx.author)

    async def confirm_action(self, ctx: commands.Context, action: str, cog_name: str) -> bool:
        """Ask for confirmation before performing a critical action."""
        confirm_message = await ctx.send(f"Are you sure you want to {action} the cog `{cog_name}`? (yes/no)")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await confirm_message.edit(content="Action timed out.")
            return False

        if msg.content.lower() != 'yes':
            await confirm_message.edit(content="Action cancelled.")
            return False

        return True

    @commands.command()
    async def load(self, ctx: commands.Context, cog: str):
        """
        Load a cog.

        Usage:
        !load <cog_name>
        """
        if not await self.confirm_action(ctx, "load", cog):
            return

        try:
            await self.bot.load_extension(f'cogs.{cog}')
            await ctx.send(f'Cog `{cog}` has been loaded.')
            logger.info(f"Cog '{cog}' loaded by {ctx.author}")
        except Exception as e:
            await ctx.send(f'Failed to load cog `{cog}`. Error: {str(e)}')
            logger.error(f"Error loading cog '{cog}': {str(e)}")

    @commands.command()
    async def unload(self, ctx: commands.Context, cog: str):
        """
        Unload a cog.

        Usage:
        !unload <cog_name>
        """
        if not await self.confirm_action(ctx, "unload", cog):
            return

        try:
            await self.bot.unload_extension(f'cogs.{cog}')
            await ctx.send(f'Cog `{cog}` has been unloaded.')
            logger.info(f"Cog '{cog}' unloaded by {ctx.author}")
        except Exception as e:
            await ctx.send(f'Failed to unload cog `{cog}`. Error: {str(e)}')
            logger.error(f"Error unloading cog '{cog}': {str(e)}")

    @commands.command()
    async def reload(self, ctx: commands.Context, cog: str):
        """
        Reload a cog.

        Usage:
        !reload <cog_name>
        """
        if not await self.confirm_action(ctx, "reload", cog):
            return

        try:
            await self.bot.reload_extension(f'cogs.{cog}')
            await ctx.send(f'Cog `{cog}` has been reloaded.')
            logger.info(f"Cog '{cog}' reloaded by {ctx.author}")
        except Exception as e:
            await ctx.send(f'Failed to reload cog `{cog}`. Error: {str(e)}')
            logger.error(f"Error reloading cog '{cog}': {str(e)}")

    @commands.command()
    async def list_cogs(self, ctx: commands.Context):
        """
        List all available cogs and their status.

        Usage:
        !list_cogs
        """
        cogs = [f[:-3] for f in os.listdir(self.cogs_dir) if f.endswith('.py')]
        loaded_cogs = [ext.split('.')[-1] for ext in self.bot.extensions]
        
        embed = discord.Embed(title="Cog Status", color=discord.Color.blue())
        for cog in cogs:
            status = "Loaded" if cog in loaded_cogs else "Unloaded"
            embed.add_field(name=cog, value=status, inline=False)
        
        await ctx.send(embed=embed)
        logger.info(f"Cog list requested by {ctx.author}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handler for command errors."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument. Usage: `{ctx.prefix}{ctx.command.name} <cog_name>`")
        elif isinstance(error, commands.NotOwner):
            await ctx.send("You must be the bot owner to use this command.")
        else:
            logger.error(f"Error in command {ctx.command}: {str(error)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(CogManager(bot))
    logger.info("CogManager cog loaded")