import discord
from discord.ext import commands
from typing import Dict, List, Optional

class CommandCategory:
    def __init__(self, name: str, description: str, commands: List[commands.Command]):
        self.name = name
        self.description = description
        self.commands = commands

class BotCapabilities(commands.Cog):
    """A cog for displaying bot capabilities and command help."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.hidden_cogs = ["CogManager", "LogViewer", "DnDRecorder"]  # Add any other cogs you want to hide
        self.categories: Dict[str, CommandCategory] = self._categorize_commands()

    def _categorize_commands(self) -> Dict[str, CommandCategory]:
        categories = {
            "AI": CommandCategory("AI", "AI-related commands", []),
            "Search": CommandCategory("Search", "Search-related commands", []),
            "Fun": CommandCategory("Fun", "Fun and entertainment commands", []),
            "Music": CommandCategory("Music", "Music playback commands", []),
            "Reminders": CommandCategory("Reminders", "Reminder-related commands", []),
            "Dice Rolling": CommandCategory("Dice Rolling", "Dice rolling and coin flipping commands", []),
            "Quotes": CommandCategory("Quotes", "Quote-related commands", []),
            "Trivia": CommandCategory("Trivia", "Trivia game commands", []),
        }

        for command in self.bot.commands:
            if command.cog_name not in self.hidden_cogs:
                if command.cog_name == "ClaudeAI":
                    categories["AI"].commands.append(command)
                elif command.cog_name == "GoogleSearch":
                    categories["Search"].commands.append(command)
                elif command.cog_name == "JokePoster":
                    categories["Fun"].commands.append(command)
                elif command.cog_name == "Music":
                    categories["Music"].commands.append(command)
                elif command.cog_name == "Reminder":
                    categories["Reminders"].commands.append(command)
                elif command.cog_name == "DiceRoller":
                    categories["Dice Rolling"].commands.append(command)
                elif command.cog_name == "QuoteCog":
                    categories["Quotes"].commands.append(command)
                elif command.cog_name == "TriviaCog":
                    categories["Trivia"].commands.append(command)

        return categories

    @commands.command(name="bothelp")
    async def display_help(self, ctx: commands.Context, command_name: Optional[str] = None):
        """
        Display bot help information.

        Usage:
        .bothelp           - Show all command categories
        .bothelp <command> - Show detailed help for a specific command
        .bothelp music     - Show an explanation of the music functionality
        .bothelp quotes    - Show an explanation of the quote functionality
        .bothelp trivia    - Show an explanation of the trivia functionality
        """
        if command_name:
            if command_name.lower() == "music":
                await self._show_music_explanation(ctx)
            elif command_name.lower() == "quotes":
                await self._show_quote_explanation(ctx)
            elif command_name.lower() == "trivia":
                await self._show_trivia_explanation(ctx)
            else:
                await self._show_command_help(ctx, command_name)
        else:
            await self._show_categories(ctx)

    async def _show_categories(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are the command categories. Use `.bothelp <command>` for detailed info on a command.",
            color=discord.Color.blue()
        )

        for category in self.categories.values():
            if category.commands:
                command_list = ", ".join(f"`{cmd.name}`" for cmd in category.commands)
                embed.add_field(name=category.name, value=f"{category.description}\nCommands: {command_list}", inline=False)

        embed.add_field(name="Music Functionality", value="Use `.bothelp music` for an explanation of how the music bot works.", inline=False)
        embed.add_field(name="Quote Functionality", value="Use `.bothelp quotes` for an explanation of how the quote system works.", inline=False)
        embed.add_field(name="Trivia Functionality", value="Use `.bothelp trivia` for an explanation of how the trivia system works.", inline=False)
        embed.add_field(name="Trivia", value="Trivia questions are provided by OpenTDB.com", inline=False)
        embed.add_field(name="Jokes", value="Jokes are provided by JokeAPI.dev", inline=False)
        await ctx.send(embed=embed)

    async def _show_command_help(self, ctx: commands.Context, command_name: str):
        command = self.bot.get_command(command_name)
        if not command or command.cog_name in self.hidden_cogs:
            await ctx.send(f"Command `{command_name}` not found.")
            return

        description = command.help or self._get_custom_description(command.name)

        embed = discord.Embed(
            title=f"Help: {command.name}",
            description=description,
            color=discord.Color.green()
        )

        usage = f"`.{command.name}"
        if command.signature:
            usage += f" {command.signature}`"
        else:
            usage += "`"
        embed.add_field(name="Usage", value=usage, inline=False)

        if isinstance(command, commands.Group):
            subcommands = "\n".join(f"`{c.name}`: {self._get_custom_description(c.name)}" for c in command.commands)
            embed.add_field(name="Subcommands", value=subcommands or "No subcommands", inline=False)

        await ctx.send(embed=embed)

    def _get_custom_description(self, command_name: str) -> str:
        descriptions = {
            "stop": "This stops the music playback and clears the queue.",
            "play": "Plays a song or adds it to the queue if something is already playing.",
            "skip": "Skips the current song and plays the next one in the queue.",
            "next": "Skips the current song and plays the next one in the queue.",
            "queue": "Shows the current music queue.",
            "leave": "Makes the bot leave the voice channel and clears the queue.",
            "triviagame": "Starts a trivia game.",
            "trivia": "Gives one trivia question.",
            "stopgame": "Stops the current trivia game.",
            "google": "Does a Google search showing top 3 results.",
            "image": "Does an image search providing top result.",
            "joke": "Tells a random joke.",
            "reminder": "Set a reminder for a specified time in the future.",
            "remindme": "Alias for 'reminder'. Set a reminder for a specified time in the future.",
            "showreminders": "Display all your active reminders.",
            "removereminder": "Remove a specific reminder by its ID.",
            "roll": "Roll one or more dice with a specified number of sides.",
            "flip": "Flip one or more coins.",
            "quoteadd": "Add a new quote for a specific name in the current server.",
            "quotedel": "Delete a specific quote for a name in the current server.",
            "quote": "Display a random quote from the current server.",
        }
        return descriptions.get(command_name, "This command performs a specific function. Use it as instructed for best results.")

    async def _show_music_explanation(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Music Bot Functionality",
            description="Here's how the music bot works:",
            color=discord.Color.purple()
        )

        embed.add_field(name="Requesting Songs", value="Use `.play <song name or URL>` to request a song. The bot will search YouTube and add the song to the queue.", inline=False)
        embed.add_field(name="Queue System", value="Songs are added to a queue. If no song is playing, the bot will immediately play the requested song. Otherwise, it will be added to the queue.", inline=False)
        embed.add_field(name="Viewing the Queue", value="Use `.queue` to see the list of upcoming songs.", inline=False)
        embed.add_field(name="Skipping Songs", value="Use `.skip` or `.next` to skip the current song and play the next one in the queue.", inline=False)
        embed.add_field(name="Stopping Playback", value="Use `.stop` to stop the current playback and clear the queue.", inline=False)
        embed.add_field(name="Disconnecting", value="Use `.leave` to make the bot leave the voice channel and clear the queue.", inline=False)
        embed.add_field(name="Note", value="The bot can only play in one voice channel per server at a time. It will automatically move to your channel if you use a command while in a different voice channel.", inline=False)

        await ctx.send(embed=embed)

    async def _show_quote_explanation(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Quote Functionality",
            description="Here's how the quote system works:",
            color=discord.Color.gold()
        )

        embed.add_field(name="Adding Quotes", value="Use `.quoteadd <name> <quote>` to add a new quote for a specific name in the current server.", inline=False)
        embed.add_field(name="Deleting Quotes", value="Use `.quotedel <name> <quote>` to delete a specific quote for a name in the current server.", inline=False)
        embed.add_field(name="Displaying Quotes", value="Use `.quote` to display a random quote from the current server.", inline=False)
        embed.add_field(name="Server-Specific", value="Quotes are server-specific, meaning each server has its own set of quotes.", inline=False)
        embed.add_field(name="Storage", value="Quotes are stored in a JSON file and persist between bot restarts.", inline=False)

        await ctx.send(embed=embed)

    async def _show_trivia_explanation(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Trivia Functionality",
            description="Here's how the trivia system works:",
            color=discord.Color.purple()
        )

        embed.add_field(name="Single Question", value="Use `.trivia` to get a single trivia question.", inline=False)
        embed.add_field(name="Full Game", value="Use `.triviagame` to start a full trivia game with multiple questions.", inline=False)
        embed.add_field(name="Game Categories", value="When starting a game, you can choose from various categories or play with mixed categories.", inline=False)
        embed.add_field(name="Joining a Game", value="Players can join by typing '1' when prompted.", inline=False)
        embed.add_field(name="Answering Questions", value="For multiple choice, type the letter (A, B, C, D). For True/False, type 'True' or 'False'.", inline=False)
        embed.add_field(name="Scoring", value="Players earn 1 point for each correct answer.", inline=False)
        embed.add_field(name="Game Duration", value="A full game consists of 10 questions.", inline=False)
        embed.add_field(name="Stopping a Game", value="The game starter can use `.stopgame` to end the game early.", inline=False)
        embed.add_field(name="Source", value="Trivia questions are provided by OpenTDB.com", inline=False)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument. Use `.bothelp {ctx.command.name}` for proper usage.")

async def setup(bot: commands.Bot):
    await bot.add_cog(BotCapabilities(bot))