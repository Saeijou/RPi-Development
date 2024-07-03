import discord
from discord.ext import commands
import json
import random
import os

class QuoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quotes_file = "quotes.json"
        self.quotes = self.load_quotes()

    def load_quotes(self):
        if os.path.exists(self.quotes_file):
            with open(self.quotes_file, "r") as f:
                return json.load(f)
        return {}

    def save_quotes(self):
        with open(self.quotes_file, "w") as f:
            json.dump(self.quotes, f, indent=2)

    def get_server_quotes(self, server_id):
        return self.quotes.get(str(server_id), {})

    @commands.command()
    async def quoteadd(self, ctx, name: str, *, quote: str):
        server_id = str(ctx.guild.id)
        if server_id not in self.quotes:
            self.quotes[server_id] = {}
        if name not in self.quotes[server_id]:
            self.quotes[server_id][name] = []
        self.quotes[server_id][name].append(quote)
        self.save_quotes()
        await ctx.send(f"Quote added for {name} in this server.")

    @commands.command()
    async def quotedel(self, ctx, name: str, *, quote: str):
        server_id = str(ctx.guild.id)
        if server_id in self.quotes and name in self.quotes[server_id] and quote in self.quotes[server_id][name]:
            self.quotes[server_id][name].remove(quote)
            if not self.quotes[server_id][name]:
                del self.quotes[server_id][name]
            if not self.quotes[server_id]:
                del self.quotes[server_id]
            self.save_quotes()
            await ctx.send(f"Quote deleted for {name} in this server.")
        else:
            await ctx.send("Quote not found in this server.")

    @commands.command()
    async def quote(self, ctx):
        server_id = str(ctx.guild.id)
        server_quotes = self.get_server_quotes(server_id)
        if not server_quotes:
            await ctx.send("No quotes available for this server.")
            return
        
        name = random.choice(list(server_quotes.keys()))
        quote = random.choice(server_quotes[name])
        await ctx.send(f"**{name}:** {quote}")

async def setup(bot):
    await bot.add_cog(QuoteCog(bot))