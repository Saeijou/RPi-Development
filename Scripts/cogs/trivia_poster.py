import discord
from discord.ext import commands
import aiohttp
import asyncio
import html
import random
from collections import defaultdict
from datetime import timedelta, datetime

class TriviaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://opentdb.com/api.php?amount=1"
        self.active_games = {}
        self.game_starters = {}
        self.cooldowns = {}
        self.categories = {
            "General Knowledge": 9,
            "Entertainment: Books": 10,
            "Entertainment: Film": 11,
            "Entertainment: Music": 12,
            "Entertainment: Musicals & Theatres": 13,
            "Entertainment: Television": 14,
            "Entertainment: Video Games": 15,
            "Entertainment: Board Games": 16,
            "Science & Nature": 17,
            "Science: Computers": 18,
            "Science: Mathematics": 19,
            "Mythology": 20,
            "Sports": 21,
            "Geography": 22,
            "History": 23,
            "Politics": 24,
            "Art": 25,
            "Celebrities": 26,
            "Animals": 27,
            "Vehicles": 28,
            "Entertainment: Comics": 29,
            "Science: Gadgets": 30,
            "Entertainment: Japanese Anime & Manga": 31,
            "Entertainment: Cartoon & Animations": 32
        }

    async def fetch_question(self, category=None):
        url = self.base_url
        if category:
            url += f"&category={category}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['results'][0]
                else:
                    return None

    @commands.command(name="trivia")
    async def trivia(self, ctx):
        if ctx.channel.id in self.cooldowns and self.cooldowns[ctx.channel.id] > datetime.utcnow():
            await ctx.send("Please wait for the current question to finish before starting a new one.")
            return

        question_data = await self.fetch_question()
        if not question_data:
            await ctx.send("Failed to fetch trivia question. Please try again later.")
            return

        self.cooldowns[ctx.channel.id] = datetime.utcnow() + timedelta(seconds=15)

        question = html.unescape(question_data['question'])
        correct_answer = html.unescape(question_data['correct_answer'])
        category = question_data['category']
        difficulty = question_data['difficulty'].capitalize()

        question_embed = discord.Embed(title="Trivia Time!", color=discord.Color.blue())
        question_embed.add_field(name="Category", value=category, inline=False)
        question_embed.add_field(name="Difficulty", value=difficulty, inline=False)
        question_embed.add_field(name="Question", value=question, inline=False)

        if question_data['type'] == "multiple":
            answers = [correct_answer] + [html.unescape(answer) for answer in question_data['incorrect_answers']]
            random.shuffle(answers)
            answer_text = "\n".join([f"{chr(65 + i)}. {answer}" for i, answer in enumerate(answers)])
            question_embed.add_field(name="Answers", value=answer_text, inline=False)
        
        await ctx.send(embed=question_embed)
        await asyncio.sleep(10)

        answer_embed = discord.Embed(title="Time's Up!", color=discord.Color.green())
        answer_embed.add_field(name="Correct Answer", value=correct_answer, inline=False)
        await ctx.send(embed=answer_embed)

    @commands.command(name="triviagame")
    async def trivia_game(self, ctx):
        if ctx.channel.id in self.active_games:
            await ctx.send("A game is already in progress in this channel.")
            return

        self.game_starters[ctx.channel.id] = ctx.author

        category_list = ["All"] + list(self.categories.keys())
        category_embed = discord.Embed(title="Trivia Game Categories", color=discord.Color.blue())
        category_text = "\n".join([f"{i+1}. {category}" for i, category in enumerate(category_list)])
        category_embed.add_field(name="Available Categories", value=category_text, inline=False)
        category_embed.add_field(name="How to Choose", value="Type the number of your desired category", inline=False)
        await ctx.send(embed=category_embed)

        def category_check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and 1 <= int(m.content) <= len(category_list)

        try:
            category_msg = await self.bot.wait_for('message', check=category_check, timeout=30.0)
            selected_category = category_list[int(category_msg.content) - 1]
        except asyncio.TimeoutError:
            await ctx.send("Category selection timed out. Using 'All' categories.")
            selected_category = "All"

        category_id = None if selected_category == "All" else self.categories[selected_category]

        instructions = discord.Embed(title="New Trivia Game!", color=discord.Color.blue())
        instructions.add_field(name="Category", value=selected_category, inline=False)
        instructions.add_field(name="How to Play", value=(
            "1. Type '1' to join the game.\n"
            "2. The game can be played solo or with multiple players.\n"
            "3. The game consists of 10 questions.\n"
            "4. For each question, type your answer in the chat.\n"
            "5. For multiple choice, type the letter of your answer (A, B, C, or D).\n"
            "6. For True/False questions, type 'True' or 'False'.\n"
            "7. You have 30 seconds to answer each question.\n"
            "8. Correct answers earn you 1 point.\n"
            "9. Try to get the highest score possible!"
        ), inline=False)
        instructions.add_field(name="Join Now", value="Type '1' to join the game!", inline=False)

        await ctx.send(embed=instructions)

        players = set()
        start_time = datetime.utcnow()

        def check(m):
            return m.content == '1' and m.channel == ctx.channel and m.author not in players

        while (datetime.utcnow() - start_time).total_seconds() < 30:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30.0 - (datetime.utcnow() - start_time).total_seconds())
                players.add(msg.author)
                await ctx.send(f"{msg.author.name} has joined! We have {len(players)} player(s).")
                if len(players) == 1:
                    await ctx.send("The game will start in 30 seconds. More players can still join!")
                    await asyncio.sleep(30)
                    break
            except asyncio.TimeoutError:
                break

        if not players:
            await ctx.send("No players joined. Game cancelled.")
            del self.game_starters[ctx.channel.id]
            return

        await ctx.send(f"Game starting with {len(players)} player(s)! Get ready for the first question!")
        self.active_games[ctx.channel.id] = True
        scores = {player: 0 for player in players}

        for round in range(1, 11):
            question_data = await self.fetch_question(category_id)
            if not question_data:
                await ctx.send("Failed to fetch trivia question. Game ended.")
                break

            question = html.unescape(question_data['question'])
            correct_answer = html.unescape(question_data['correct_answer'])
            category = question_data['category']
            difficulty = question_data['difficulty'].capitalize()

            question_embed = discord.Embed(title=f"Question {round}/10", color=discord.Color.blue())
            question_embed.add_field(name="Category", value=category, inline=False)
            question_embed.add_field(name="Difficulty", value=difficulty, inline=False)
            question_embed.add_field(name="Question", value=question, inline=False)

            if question_data['type'] == "multiple":
                answers = [correct_answer] + [html.unescape(answer) for answer in question_data['incorrect_answers']]
                random.shuffle(answers)
                answer_text = "\n".join([f"{chr(65 + i)}. {answer}" for i, answer in enumerate(answers)])
                question_embed.add_field(name="Answers", value=answer_text, inline=False)
                question_embed.add_field(name="How to Answer", value="Type the letter of your answer (A, B, C, or D)", inline=False)
                correct_letter = chr(65 + answers.index(correct_answer))
            else:
                question_embed.add_field(name="How to Answer", value="Type 'True' or 'False'", inline=False)
            
            question_embed.add_field(name="Time Limit", value="You have 30 seconds to answer!", inline=False)
            
            await ctx.send(embed=question_embed)

            answered_players = set()
            player_answers = {}

            def answer_check(m):
                return m.author in players and m.author not in answered_players and m.channel == ctx.channel

            while len(answered_players) < len(players):
                try:
                    msg = await self.bot.wait_for('message', check=answer_check, timeout=30.0)
                    answered_players.add(msg.author)
                    player_answers[msg.author] = msg.content.upper()
                    await ctx.send(f"{msg.author.name} has answered!")
                except asyncio.TimeoutError:
                    break

            if ctx.channel.id not in self.active_games:
                await ctx.send("The game has been stopped.")
                return

            answer_embed = discord.Embed(title="Round Results", color=discord.Color.green())
            if question_data['type'] == "multiple":
                answer_embed.add_field(name="Correct Answer", value=f"{correct_letter}. {correct_answer}", inline=False)
            else:
                answer_embed.add_field(name="Correct Answer", value=correct_answer, inline=False)

            for player in players:
                if player in player_answers:
                    if question_data['type'] == "multiple":
                        if player_answers[player] == correct_letter:
                            scores[player] += 1
                            answer_embed.add_field(name=player.name, value="Correct! +1 point", inline=False)
                        else:
                            answer_embed.add_field(name=player.name, value=f"Incorrect. Answered: {player_answers[player]}", inline=False)
                    else:
                        if player_answers[player] == correct_answer.upper():
                            scores[player] += 1
                            answer_embed.add_field(name=player.name, value="Correct! +1 point", inline=False)
                        else:
                            answer_embed.add_field(name=player.name, value=f"Incorrect. Answered: {player_answers[player]}", inline=False)
                else:
                    answer_embed.add_field(name=player.name, value="Did not answer in time", inline=False)

            await ctx.send(embed=answer_embed)
            
            score_update = discord.Embed(title="Current Scores", color=discord.Color.gold())
            for player, score in scores.items():
                score_update.add_field(name=player.name, value=f"{score} point{'s' if score != 1 else ''}", inline=False)
            await ctx.send(embed=score_update)
            
            await asyncio.sleep(5)

        del self.active_games[ctx.channel.id]
        del self.game_starters[ctx.channel.id]

        final_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        leaderboard = discord.Embed(title="Final Scores", color=discord.Color.gold())
        for i, (player, score) in enumerate(final_scores, 1):
            leaderboard.add_field(name=f"{i}. {player.name}", value=f"{score} point{'s' if score != 1 else ''}", inline=False)

        await ctx.send(embed=leaderboard)
        
        winner, top_score = final_scores[0]
        if len(players) > 1:
            await ctx.send(f"🎉 Congratulations to {winner.mention} for winning with {top_score} point{'s' if top_score != 1 else ''}! 🎉")
        else:
            await ctx.send(f"🎉 Congratulations, {winner.mention}! You scored {top_score} point{'s' if top_score != 1 else ''}! 🎉")

    @commands.command(name="stopgame")
    async def stop_game(self, ctx):
        if ctx.channel.id not in self.active_games:
            await ctx.send("There is no active trivia game in this channel.")
            return

        if ctx.author != self.game_starters.get(ctx.channel.id):
            await ctx.send("Only the person who started the game can stop it.")
            return

        del self.active_games[ctx.channel.id]
        del self.game_starters[ctx.channel.id]

async def setup(bot):
    await bot.add_cog(TriviaCog(bot))