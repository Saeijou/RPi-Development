import random
import re
from discord.ext import commands

class DiceRoller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='roll')
    async def roll_dice(self, ctx, *, dice_input: str):
        dice_pattern = r'(\d+)d(\d+)'
        dice_matches = re.findall(dice_pattern, dice_input)
        
        if not dice_matches:
            await ctx.send("Invalid input. Please use the format: `.roll XdY [AdB] [CdD] ...`")
            return

        results = []
        total_sum = 0

        for match in dice_matches:
            num_dice, num_sides = map(int, match)
            
            if num_dice <= 0 or num_sides <= 0:
                await ctx.send("Number of dice and sides must be positive integers.")
                return
            
            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            results.append((num_dice, num_sides, rolls))
            total_sum += sum(rolls)

        response = "🎲 Dice Roll Results:\n"
        for num_dice, num_sides, rolls in results:
            roll_sum = sum(rolls)
            response += f"{num_dice}d{num_sides}: {rolls} (Sum: {roll_sum})\n"

        response += f"\nTotal Sum: {total_sum}"
        await ctx.send(response)

    @commands.command(name='flip')
    async def flip_coin(self, ctx, number: int = 1):
        if number <= 0:
            await ctx.send("Please enter a positive number of coins to flip.")
            return
        
        if number > 1000:
            await ctx.send("That's too many coins! Please try flipping 1000 or fewer coins.")
            return

        results = [random.choice(["Heads", "Tails"]) for _ in range(number)]
        heads_count = results.count("Heads")
        tails_count = results.count("Tails")

        if number == 1:
            response = f"🪙 Coin Flip Result: **{results[0]}**"
        else:
            response = f"🪙 Flipped {number} coins:\n"
            response += f"Heads: {heads_count}\n"
            response += f"Tails: {tails_count}\n"
            if number <= 10:
                response += f"Results: {', '.join(results)}"

        await ctx.send(response)

async def setup(bot):
    await bot.add_cog(DiceRoller(bot))