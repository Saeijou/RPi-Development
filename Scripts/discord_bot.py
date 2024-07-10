import discord
from discord.ext import commands
import os
import asyncio
import logging
import configparser
import aiohttp

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))
TOKEN = config['Discord']['TOKEN']
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)
COGS_DIR = config['Paths']['cogs_folder']

# Configure logging
logging.basicConfig(filename=config['Paths']['bot_log_file'], level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(message)s')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        logging.info(f"Command not found: {ctx.message.content}")
        # Optionally, you can send a message to the user
        # await ctx.send("Sorry, I don't recognize that command.")
    else:
        raise error  # Re-raise the error if it's not a CommandNotFound error
    
@bot.event
async def on_ready():
    logging.info(f'We have logged in as {bot.user}')

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

async def main():
    await load_extensions()
    
    while True:
        try:
            await bot.start(TOKEN)
        except discord.errors.ConnectionClosed:
            logging.warning("Connection closed. Retrying in 5 seconds...")
        except aiohttp.ClientConnectionError:
            logging.warning("Connection error. Retrying in 5 seconds...")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        
        await asyncio.sleep(5)  # Wait for 5 seconds before retrying

if __name__ == "__main__":
    asyncio.run(main())