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
        self.categories: Dict[str, CommandCategory] = self._categorize_commands()

    def _categorize_commands(self) -> Dict[str, CommandCategory]:
        categories = {
            "General": CommandCategory("General", "General bot commands", []),
            "AI": CommandCategory("AI", "AI-related commands", []),
            "Search": CommandCategory("Search", "Search-related commands", []),
            "Fun": CommandCategory("Fun", "Fun and entertainment commands", []),
            "Admin": CommandCategory("Admin", "Administrative commands", []),
            "Logs": CommandCategory("Logs", "Log viewing commands", []),
        }

        for command in self.bot.commands:
            if command.cog_name == "ClaudeAI":
                categories["AI"].commands.append(command)
            elif command.cog_name == "GoogleSearch":
                categories["Search"].commands.append(command)
            elif command.cog_name == "JokePoster":
                categories["Fun"].commands.append(command)
            elif command.cog_name == "CogManager":
                categories["Admin"].commands.append(command)
            elif command.cog_name == "LogViewer":
                categories["Logs"].commands.append(command)
            else:
                categories["General"].commands.append(command)

        return categories

    @commands.command(name="bothelp")
    async def display_help(self, ctx: commands.Context, command_name: Optional[str] = None):
        """
        Display bot help information.

        Usage:
        !bothelp           - Show all command categories
        !bothelp <command> - Show detailed help for a specific command
        """
        if command_name:
            await self._show_command_help(ctx, command_name)
        else:
            await self._show_categories(ctx)

    async def _show_categories(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are the command categories. Use `!bothelp <command>` for detailed info on a command.",
            color=discord.Color.blue()
        )

        for category in self.categories.values():
            if category.commands:
                command_list = ", ".join(f"`{cmd.name}`" for cmd in category.commands)
                embed.add_field(name=category.name, value=f"{category.description}\nCommands: {command_list}", inline=False)

        embed.set_footer(text="Note: Some commands are restricted to authorized users or the bot owner only.")
        await ctx.send(embed=embed)

    async def _show_command_help(self, ctx: commands.Context, command_name: str):
        command = self.bot.get_command(command_name)
        if not command:
            await ctx.send(f"Command `{command_name}` not found.")
            return

        embed = discord.Embed(
            title=f"Help: {command.name}",
            description=command.help or "No description available.",
            color=discord.Color.green()
        )

        usage = f"`!{command.name}"
        if command.signature:
            usage += f" {command.signature}`"
        else:
            usage += "`"
        embed.add_field(name="Usage", value=usage, inline=False)

        if isinstance(command, commands.Group):
            subcommands = "\n".join(f"`{c.name}`: {c.short_doc or 'No description'}" for c in command.commands)
            embed.add_field(name="Subcommands", value=subcommands or "No subcommands", inline=False)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Command not found. Use `!bothelp` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument. Use `!bothelp {ctx.command.name}` for proper usage.")

async def setup(bot: commands.Bot):
    await bot.add_cog(BotCapabilities(bot))
    print("BotCapabilities cog loaded")