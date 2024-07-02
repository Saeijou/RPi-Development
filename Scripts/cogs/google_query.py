import discord
from discord.ext import commands
import aiohttp
import asyncio
import configparser
import os
from typing import List, Dict, Any
import logging
from functools import lru_cache
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

class GoogleSearch(commands.Cog):
    """A cog for performing Google searches."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.environ.get('GOOGLE_API_KEY') or config['Google']['API-KEY']
        self.search_engine_id = config['Google']['ENGINE_ID']
        self.base_url = 'https://www.googleapis.com/customsearch/v1'
        self.session = None
        self.cache_ttl = timedelta(hours=1)  # Cache results for 1 hour

    def cog_unload(self):
        """Clean up the aiohttp session when the cog is unloaded."""
        if self.session:
            asyncio.create_task(self.session.close())

    async def get_session(self) -> aiohttp.ClientSession:
        """Create or return an existing aiohttp ClientSession."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    @lru_cache(maxsize=100)
    async def cached_search(self, query: str, search_type: str = None) -> List[Dict[str, Any]]:
        """Perform a cached Google search."""
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query
        }
        if search_type:
            params['searchType'] = search_type

        session = await self.get_session()
        try:
            async with session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('items', [])
                else:
                    logger.error(f"Google API error: {response.status} - {await response.text()}")
                    return []
        except aiohttp.ClientError as e:
            logger.error(f"Network error during Google search: {str(e)}")
            return []

    @commands.command(name="google")
    async def google(self, ctx: commands.Context, *, query: str):
        """
        Perform a Google search and return the top 3 results.

        Usage:
        !google <query>
        """
        await ctx.typing()
        results = await self.cached_search(query)
        if results:
            response = "\n\n".join([f"**{item['title']}**\n{item['snippet']}\n{item['link']}" for item in results[:3]])
            embed = discord.Embed(title=f"Google Search Results for '{query}'", description=response, color=discord.Color.blue())
        else:
            embed = discord.Embed(title="No Results", description=f"No results found for '{query}'", color=discord.Color.red())
        
        await ctx.send(embed=embed)

    @commands.command(name="image")
    async def image(self, ctx: commands.Context, *, query: str):
        """
        Perform a Google image search and return the first result.

        Usage:
        !image <query>
        """
        await ctx.typing()
        results = await self.cached_search(query, search_type='image')
        if results:
            image_url = results[0]['link']
            embed = discord.Embed(title=f"Image Search Result for '{query}'", color=discord.Color.green())
            embed.set_image(url=image_url)
        else:
            embed = discord.Embed(title="No Results", description=f"No image found for '{query}'", color=discord.Color.red())
        
        await ctx.send(embed=embed)

    @google.error
    @image.error
    async def search_error(self, ctx: commands.Context, error: commands.CommandError):
        """Error handler for search commands."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide a search query. Usage: `!google <query>` or `!image <query>`")
        else:
            await ctx.send(f"An error occurred: {str(error)}")
            logger.error(f"Error in search command: {str(error)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(GoogleSearch(bot))