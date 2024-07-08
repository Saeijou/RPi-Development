import discord
from discord.ext import commands
import asyncio
import os
import sys
import logging
import json
import configparser

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

# Get the cogs directory from config
cogs_dir = config['Paths']['cogs_folder']

# Add the 'games' directory to the Python path
games_dir = os.path.join(cogs_dir, 'games')
sys.path.append(games_dir)

# Set up logging
logging.basicConfig(filename=config['Paths']['bot_log_file'], level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        self.highscores_file = os.path.join(cogs_dir, 'json', 'highscores.json')
        self.highscores = self.load_highscores()
        logger.info("Cog initialized")

    def load_highscores(self):
        if os.path.exists(self.highscores_file):
            with open(self.highscores_file, 'r') as f:
                return json.load(f)
        return {}

    def save_highscores(self):
        with open(self.highscores_file, 'w') as f:
            json.dump(self.highscores, f)

    def update_highscore(self, game_name, player_id, player_name, score, guild_id):
        if game_name not in self.highscores:
            self.highscores[game_name] = {}
        if str(guild_id) not in self.highscores[game_name]:
            self.highscores[game_name][str(guild_id)] = {}
        
        player_scores = self.highscores[game_name][str(guild_id)]
        if str(player_id) not in player_scores or score > player_scores[str(player_id)]['score']:
            player_scores[str(player_id)] = {'name': player_name, 'score': score}
            self.save_highscores()
            return True
        return False

    @commands.command()
    async def game(self, ctx):
        """Start a new game"""
        logger.info(f"Game command initiated by {ctx.author}")
        if ctx.author.id in self.active_games:
            await ctx.send("You already have an active game. Please finish it before starting a new one.")
            logger.info(f"Rejected game start for {ctx.author} due to existing active game")
            return

        await ctx.send(f"Check your DMs to start a new game!")
        await self.start_game_dialogue(ctx.author, ctx.guild.id)

    async def start_game_dialogue(self, player, guild_id):
        logger.info(f"Starting game dialogue for {player}")
        game_list = "\n".join([f"{key}. {name}" for key, (name, _) in self.games.items()])
        await player.send(f"Available games:\n{game_list}\nEnter the number of the game you want to play:")

        def check(m):
            return m.author == player and isinstance(m.channel, discord.DMChannel)

        try:
            choice_msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            choice = choice_msg.content
            logger.info(f"Player {player} chose game number: {choice}")

            if choice in self.games:
                game_name, game_class = self.games[choice]
                await player.send(f"Starting {game_name}.")
                
                game = game_class()
                self.active_games[player.id] = (game, player, guild_id)
                
                logger.info(f"Starting game {game_name} for player {player}")
                await self.play_game(player)
            else:
                await player.send("Invalid choice. Please use the .game command again and select a valid number.")
                logger.warning(f"Invalid game choice by {player}: {choice}")
        except asyncio.TimeoutError:
            await player.send("Game selection timed out. Please use the .game command again if you want to play.")
            logger.warning(f"Game selection timed out for {player}")

    async def play_game(self, player):
        logger.info(f"Entering play_game method for player {player}")
        game, _, guild_id = self.active_games[player.id]
        
        play_result = game.play()
        
        if isinstance(play_result, dict):
            intro_message = play_result.get("message", "Welcome to the game!")
            image_path = play_result.get("image_path")
        else:
            intro_message = play_result
            image_path = None

        logger.debug(f"Intro message: {intro_message}")
        logger.debug(f"Image path: {image_path}")
        
        # Send the image if path is provided
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as f:
                    picture = discord.File(f)
                    await player.send(file=picture)
            except Exception as e:
                logger.error(f"Error sending image: {e}")
                await player.send("Sorry, I couldn't send the game map image.")
        
        # Send the intro message
        await player.send(intro_message)
        await player.send("Game started. You can now enter commands.")
        
        def check(m):
            return m.author == player and isinstance(m.channel, discord.DMChannel)

        while not game.is_game_over:
            try:
                response = await self.bot.wait_for('message', check=check, timeout=300.0)
                
                logger.debug(f"Received command from {player}: {response.content}")
                output = game.process_command(response.content)
                logger.debug(f"Game response for {player}: {output}")
                
                await player.send(output)
                
            except asyncio.TimeoutError:
                await player.send("Game timed out due to inactivity.")
                logger.warning(f"Game timed out for {player}")
                break
        
        final_score = game.score
        await player.send(f"Game over! Your final score: {final_score} points.")
        
        game_name = self.games[next(key for key, value in self.games.items() if isinstance(game, value[1]))][0]
        is_new_highscore = self.update_highscore(game_name, player.id, str(player), final_score, guild_id)
        if is_new_highscore:
            await player.send("Congratulations! You've set a new personal highscore!")
        
        del self.active_games[player.id]
        logger.info(f"Removed game for {player} from active games")

    @commands.command()
    async def score(self, ctx):
        """Display highscores for the server"""
        guild_id = str(ctx.guild.id)
        highscores_message = "Highscores:\n"
        for game_name, guild_scores in self.highscores.items():
            if guild_id in guild_scores:
                highscores_message += f"\n{game_name}:\n"
                sorted_scores = sorted(guild_scores[guild_id].items(), key=lambda x: x[1]['score'], reverse=True)
                for i, (player_id, data) in enumerate(sorted_scores[:5], 1):
                    highscores_message += f"{i}. {data['name']}: {data['score']} points\n"
        
        if highscores_message == "Highscores:\n":
            await ctx.send("No highscores recorded for this server yet.")
        else:
            await ctx.send(highscores_message)

async def setup(bot):
    await bot.add_cog(Cog(bot))