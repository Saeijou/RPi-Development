import discord
from discord.ext import commands, tasks
import re
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')

class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = {}
        self.reminder_file = "reminders.json"
        self.load_reminders()
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @commands.command(aliases=['remindme'])
    async def reminder(self, ctx, time_input: str, *, message: str):
        total_seconds = self.parse_time(time_input)
        
        if total_seconds is None:
            await ctx.send("Invalid time format. Use a number followed by d, h, m, or s (e.g., '5d', '3h', '30m', '1d6h').")
            return

        if total_seconds <= 0:
            await ctx.send("Please specify a time in the future.")
            return

        remind_time = datetime.utcnow() + timedelta(seconds=total_seconds)
        reminder_id = str(ctx.message.id)
        reminder = {
            "id": reminder_id,
            "user_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "remind_time": remind_time.isoformat(),
            "message": message,
            "original_channel": ctx.channel.name
        }

        self.reminders[reminder_id] = reminder
        self.save_reminders()

        await ctx.send(f"I'll remind you at {remind_time.strftime('%Y-%m-%d %H:%M:%S')} UTC with the message: {message}")

        logging.info(f"Set reminder: {reminder}")

    def parse_time(self, time_str: str) -> Optional[int]:
        pattern = r'(\d+)([dhms])'
        matches = re.findall(pattern, time_str.lower())
        
        if not matches:
            return None

        total_seconds = 0
        for value, unit in matches:
            value = int(value)
            if unit == 'd':
                total_seconds += value * 86400
            elif unit == 'h':
                total_seconds += value * 3600
            elif unit == 'm':
                total_seconds += value * 60
            elif unit == 's':
                total_seconds += value

        return total_seconds

    @commands.command()
    async def showreminders(self, ctx):
        user_reminders = [r for r in self.reminders.values() if r['user_id'] == ctx.author.id]
        
        if not user_reminders:
            await ctx.send("You don't have any active reminders.")
            return

        embed = discord.Embed(title="Your Active Reminders", color=discord.Color.blue())
        for reminder in user_reminders:
            remind_time = datetime.fromisoformat(reminder['remind_time'])
            time_left = remind_time - datetime.utcnow()
            embed.add_field(
                name=f"Reminder (ID: {reminder['id']})",
                value=f"Message: {reminder['message']}\n"
                      f"Time: {remind_time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                      f"Time left: {self.format_time_difference(time_left.total_seconds())}\n"
                      f"Channel: {reminder['original_channel']}",
                inline=False
            )

        await ctx.send(embed=embed)

    def format_time_difference(self, seconds):
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        return " ".join(parts)

    @tasks.loop(seconds=5)
    async def check_reminders(self):
        current_time = datetime.utcnow()
        reminders_to_remove = []

        for reminder_id, reminder in self.reminders.items():
            remind_time = datetime.fromisoformat(reminder["remind_time"])
            if remind_time <= current_time:
                await self.send_reminder(reminder)
                reminders_to_remove.append(reminder_id)

        for reminder_id in reminders_to_remove:
            del self.reminders[reminder_id]

        if reminders_to_remove:
            self.save_reminders()

    async def send_reminder(self, reminder):
        user = self.bot.get_user(reminder["user_id"])
        if user is None:
            user = await self.bot.fetch_user(reminder["user_id"])

        if user:
            try:
                await user.send(f"Reminder from {reminder['original_channel']}: {reminder['message']}")
                logging.info(f"Sent reminder {reminder['id']} to user {user.id} via DM")
            except discord.errors.Forbidden:
                logging.warning(f"Couldn't send DM to user {user.id}, attempting to send in original channel")
                channel = self.bot.get_channel(reminder["channel_id"])
                if channel:
                    await channel.send(f"{user.mention}, I couldn't send you a DM. Here's your reminder: {reminder['message']}")
                    logging.info(f"Sent reminder {reminder['id']} to channel {channel.id}")
                else:
                    logging.error(f"Couldn't find channel {reminder['channel_id']} to send reminder {reminder['id']}")
        else:
            logging.error(f"Couldn't find user {reminder['user_id']} for reminder {reminder['id']}")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    def save_reminders(self):
        with open(self.reminder_file, 'w') as f:
            json.dump(self.reminders, f, indent=4)
        logging.info(f"Saved {len(self.reminders)} reminders to file")

    def load_reminders(self):
        try:
            with open(self.reminder_file, 'r') as f:
                self.reminders = json.load(f)
            logging.info(f"Loaded {len(self.reminders)} reminders from file")
        except FileNotFoundError:
            self.reminders = {}
            logging.info("No reminders file found, starting with empty reminders")

    @commands.command()
    async def removereminder(self, ctx, reminder_id: str):
        if reminder_id not in self.reminders:
            await ctx.send(f"No reminder found with ID {reminder_id}.")
            return

        reminder = self.reminders[reminder_id]
        
        if ctx.author.id != reminder['user_id']:
            await ctx.send("You are not authorized to remove this reminder.")
            return

        del self.reminders[reminder_id]
        self.save_reminders()

        await ctx.send(f"Reminder with ID {reminder_id} has been removed.")
        logging.info(f"Removed reminder {reminder_id} for user {ctx.author.id}")

async def setup(bot):
    await bot.add_cog(Reminder(bot))