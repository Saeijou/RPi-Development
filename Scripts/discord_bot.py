import discord
from discord.ext import commands
import os
import asyncio
import logging
import configparser

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

TOKEN = config['Discord']['TOKEN']

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

COGS_DIR = config['Paths']['cogs_folder']

# Configure logging
logging.basicConfig(filename=config['Paths']['bot_log_file'], level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

@bot.event
async def on_ready():
    logging.info(f'We have logged in as {bot.user}')
    bot.loop.create_task(check_for_new_cogs())

async def load_extensions():
    if os.path.exists(COGS_DIR) and os.path.isdir(COGS_DIR):
        for filename in os.listdir(COGS_DIR):
            if filename.endswith(".py"):
                try:
                    await bot.load_extension(f"cogs.{filename[:-3]}")
                    logging.info(f"Loaded extension: {filename[:-3]}")
                except Exception as e:
                    logging.error(f"Failed to load extension {filename}: {e}")
    else:
        logging.error(f"Directory '{COGS_DIR}' does not exist")

async def check_for_new_cogs():
    while True:
        if os.path.exists(COGS_DIR) and os.path.isdir(COGS_DIR):
            cogs = set([f[:-3] for f in os.listdir(COGS_DIR) if f.endswith('.py')])
            loaded_cogs = set([ext.split('.')[-1] for ext in bot.extensions])
            new_cogs = cogs - loaded_cogs
            for cog in new_cogs:
                try:
                    await bot.load_extension(f'cogs.{cog}')
                    logging.info(f"Loaded new cog: {cog}")
                except Exception as e:
                    logging.error(f"Failed to load new cog {cog}: {e}")
        else:
            logging.error(f"Directory '{COGS_DIR}' does not exist")
        await asyncio.sleep(60)  # Check every 60 seconds

async def main():
    await load_extensions()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
