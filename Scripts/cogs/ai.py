import discord
from discord.ext import commands
import anthropic
import asyncio
import logging
from collections import defaultdict
import configparser
import os
from typing import Dict, Any
import time

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

class ClaudeAI(commands.Cog):
    """A cog for interacting with Claude AI."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Read config
        self.config = configparser.ConfigParser()
        self.config.read(os.path.expanduser('~/Python/.config'))
        
        self.claude = anthropic.Anthropic(api_key=self.config['Anthropic']['API-KEY'])
        self.allowed_users = self.config['AI']['allowed_users'].split(',')
        self.input_cost_per_1m_tokens = float(self.config['AI']['input_cost_per_1m_tokens'])
        self.output_cost_per_1m_tokens = float(self.config['AI']['output_cost_per_1m_tokens'])
        self.user_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total_input_tokens": 0, "total_output_tokens": 0, "total_cost": 0.0, "last_use": 0})
        self.rate_limit = float(self.config['AI']['rate_limit'])  # in seconds

    @commands.command(name="ai")
    async def ai_response(self, ctx: commands.Context, *, phrase: str):
        """Generate a response using Claude AI."""
        logger.info(f"Command 'ai' used by {ctx.author.name} with question: {phrase}")
        
        if ctx.author.name.lower() not in self.allowed_users:
            await ctx.send("Sorry, you're not authorized to use this command.")
            logger.warning(f"Unauthorized 'ai' command attempt by {ctx.author.name}")
            return

        # Rate limiting
        current_time = time.time()
        if current_time - self.user_stats[ctx.author.name.lower()]["last_use"] < self.rate_limit:
            await ctx.send(f"Please wait {self.rate_limit} seconds between requests.")
            return
        self.user_stats[ctx.author.name.lower()]["last_use"] = current_time

        try:
            message = await ctx.send("Thinking...")

            response = await asyncio.to_thread(
                self.claude.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": phrase}
                ]
            )

            ai_response = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            input_cost = (input_tokens / 1_000_000) * self.input_cost_per_1m_tokens
            output_cost = (output_tokens / 1_000_000) * self.output_cost_per_1m_tokens
            total_cost = input_cost + output_cost

            # Update user stats
            user_stats = self.user_stats[ctx.author.name.lower()]
            user_stats["total_input_tokens"] += input_tokens
            user_stats["total_output_tokens"] += output_tokens
            user_stats["total_cost"] += total_cost

            await message.edit(content=f"Claude: {ai_response}\n\n"
                                       f"Tokens used: {total_tokens} "
                                       f"(Input: {input_tokens}, Output: {output_tokens})\n"
                                       f"Estimated cost: ${total_cost:.6f} "
                                       f"(Input: ${input_cost:.6f}, Output: ${output_cost:.6f})")
            
            logger.info(f"AI response given to {ctx.author.name}: {ai_response}")

        except anthropic.APIError as e:
            await ctx.send(f"An error occurred with the AI service: {str(e)}")
            logger.error(f"Anthropic API error in 'ai' command used by {ctx.author.name}: {e}")
        except Exception as e:
            await ctx.send("An unexpected error occurred. Please try again later.")
            logger.error(f"Unexpected error in 'ai' command used by {ctx.author.name}: {e}")

    @commands.command(name="aistats")
    async def ai_stats(self, ctx: commands.Context):
        """View AI usage statistics."""
        logger.info(f"Command 'aistats' used by {ctx.author.name}")
        if ctx.author.name.lower() not in self.allowed_users:
            await ctx.send("Sorry, you're not authorized to use this command.")
            logger.warning(f"Unauthorized 'aistats' command attempt by {ctx.author.name}")
            return

        user_stats = self.user_stats[ctx.author.name.lower()]
        total_input_tokens = user_stats["total_input_tokens"]
        total_output_tokens = user_stats["total_output_tokens"]
        total_cost = user_stats["total_cost"]

        await ctx.send(f"AI Usage Stats for {ctx.author.name}:\n"
                       f"Total input tokens: {total_input_tokens}\n"
                       f"Total output tokens: {total_output_tokens}\n"
                       f"Total estimated cost: ${total_cost:.6f}")
        logger.info(f"AI stats provided to {ctx.author.name}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ClaudeAI(bot))