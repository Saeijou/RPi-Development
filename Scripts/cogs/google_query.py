import discord
from discord.ext import commands
import aiohttp
import configparser

# Read config
config = configparser.ConfigParser()
config.read('/home/pi/Python/.config')

class GoogleSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = config['Google']['API-KEY']
        self.search_engine_id = config['Google']['ENGINE_ID']
        self.base_url = 'https://www.googleapis.com/customsearch/v1'

    async def perform_search(self, query, search_type=None):
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': query
        }
        if search_type:
            params['searchType'] = search_type

        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('items', [])
                else:
                    return None

    @commands.command()
    async def google(self, ctx, *, query):
        results = await self.perform_search(query)
        if results:
            response = "\n".join([item['link'] for item in results[:3]])
            await ctx.send(f"Top 3 results for '{query}':\n{response}")
        else:
            await ctx.send(f"No results found for '{query}'")

    @commands.command()
    async def image(self, ctx, *, query):
        results = await self.perform_search(query, search_type='image')
        if results:
            image_url = results[0]['link']
            await ctx.send(image_url)
        else:
            await ctx.send(f"No image found for '{query}'")

async def setup(bot):
    await bot.add_cog(GoogleSearch(bot))