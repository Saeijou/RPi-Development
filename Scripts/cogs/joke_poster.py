import discord
from discord.ext import commands
import aiohttp

class JokePoster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="joke")
    async def tell_joke(self, ctx):
        joke = await self.fetch_joke()
        if joke:
            if joke['type'] == 'single':
                await ctx.send(f"Here's a joke:\n\n{joke['joke']}")
            else:
                await ctx.send(f"Here's a joke:\n\n{joke['setup']}\n\n{joke['delivery']}")
        else:
            await ctx.send("Sorry, I couldn't fetch a joke at the moment.")

    async def fetch_joke(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://v2.jokeapi.dev/joke/Any?safe-mode') as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None

async def setup(bot):
    await bot.add_cog(JokePoster(bot))