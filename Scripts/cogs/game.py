import discord
from discord.ext import commands
import asyncio
import os
import sys
import logging
import configparser

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

# Configure logging
logging.basicConfig(filename=config['Paths']['bot_log_file'], level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

# Add the 'games' directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
games_dir = os.path.join(current_dir, 'games')
sys.path.append(games_dir)

# Now import the Game class
try:
    from ruins_of_new_york import Game
    logger.info("Successfully imported Game class")
except ImportError as e:
    logger.error(f"Error importing Game class: {e}")
    raise

class Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.games = {
            "1": ("Ruins of New York", Game)
        }
        logger.info("Cog initialized")

    @commands.command()
    async def game(self, ctx):
        """Start a new game"""
        logger.info(f"Game command initiated by {ctx.author}")
        if ctx.author.id in self.active_games:
            await ctx.send("You already have an active game. Please finish it before starting a new one.")
            logger.info(f"Rejected game start for {ctx.author} due to existing active game")
            return

        await ctx.send(f"Check your DMs to start a new game!")
        await self.start_game_dialogue(ctx.author)

    async def start_game_dialogue(self, player):
        logger.info(f"Starting game dialogue for {player}")
        # Display available games
        game_list = "\n".join([f"{key}. {name}" for key, (name, _) in self.games.items()])
        await player.send(f"Available games:\n{game_list}\nEnter the number of the game you want to play:")

        try:
            # Wait for the user's choice
            choice_msg = await self.bot.wait_for('message', 
                check=lambda m: m.author == player and isinstance(m.channel, discord.DMChannel), 
                timeout=30.0
            )
            choice = choice_msg.content
            logger.info(f"Player {player} chose game number: {choice}")

            if choice in self.games:
                game_name, game_class = self.games[choice]
                await player.send(f"Starting {game_name}.")
                
                # Create a new game instance
                game = game_class()
                
                # Store the game instance and player
                self.active_games[player.id] = (game, player)
                
                logger.info(f"Starting game {game_name} for player {player}")
                
                # Start the game
                await self.play_game(player)
            else:
                await player.send("Invalid choice. Please use the .game command again and select a valid number.")
                logger.warning(f"Invalid game choice by {player}: {choice}")
        except asyncio.TimeoutError:
            await player.send("Game selection timed out. Please use the .game command again if you want to play.")
            logger.warning(f"Game selection timed out for {player}")

    async def play_game(self, player):
        logger.info(f"Entering play_game method for player {player}")
        game, _ = self.active_games[player.id]
        
        # Send initial game message
        intro_message = game.play()
        logger.debug(f"Intro message: {intro_message}")
        for line in intro_message.split('\n'):
            await player.send(line)
        
        await player.send("Game started. You can now enter commands.")
        
        while True:
            try:
                # Wait for player's response
                response = await self.bot.wait_for('message', 
                    check=lambda m: m.author == player and isinstance(m.channel, discord.DMChannel), 
                    timeout=300.0
                )
                
                logger.debug(f"Received command from {player}: {response.content}")
                
                # Process the player's input
                output = game.process_command(response.content)
                
                logger.debug(f"Game response for {player}: {output}")
                
                # Send the output in chunks to avoid hitting Discord's message length limit
                for i in range(0, len(output), 2000):
                    await player.send(output[i:i+2000])
                
                # Check if the game is over
                if game.is_game_over:
                    logger.info(f"Game over for {player}")
                    break
            except asyncio.TimeoutError:
                await player.send("Game timed out due to inactivity.")
                logger.warning(f"Game timed out for {player}")
                break
        
        # Game is over, announce the score
        await player.send(f"Game over! Your final score: {game.score} points.")
        
        # Remove the game from active games
        del self.active_games[player.id]
        logger.info(f"Removed game for {player} from active games")

async def setup(bot):
    await bot.add_cog(Cog(bot))
    logger.info("Cog setup complete")