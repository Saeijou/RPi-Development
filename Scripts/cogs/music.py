import discord
from discord.ext import commands, tasks
import yt_dlp
import asyncio
import configparser
import os
import random
from googleapiclient.discovery import build
import time
import logging

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

# Set up YouTube API client
DEVELOPER_KEY = config['Youtube']['API-KEY']
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

# YouTube Premium account credentials
EMAIL = config['Youtube']['Email']
PASSWORD = config['Youtube']['Password']

# yt-dlp options
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'username': EMAIL,
    'password': PASSWORD,
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

# Add this line
discord.utils.setup_logging(level=logging.INFO, root=False)

async def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)

async def search_youtube(query):
    search_opts = ydl_opts.copy()
    search_opts.update({
        'default_search': 'ytsearch',
        'no_warnings': True,
        'quiet': True
    })
    
    async def search():
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return {'url': info['url'], 'title': info['title']}

    try:
        return await retry_with_backoff(search)
    except Exception as e:
        print(f"An error occurred in search_youtube: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        self.current_song = {}
        self.last_activity = {}
        self.last_member_time = {}
        self.check_inactivity.start()

    def cog_unload(self):
        self.check_inactivity.cancel()

    def reset_activity_timer(self, guild_id):
        self.last_activity[guild_id] = time.time()

    async def disconnect_and_cleanup(self, guild):
        if guild.voice_client:
            await guild.voice_client.disconnect()
        self.queue.pop(guild.id, None)
        self.current_song.pop(guild.id, None)
        self.last_activity.pop(guild.id, None)
        self.last_member_time.pop(guild.id, None)
        print(f"Disconnected from {guild.name} due to inactivity")

    @tasks.loop(seconds=60)
    async def check_inactivity(self):
        for guild_id in list(self.last_activity.keys()):
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                voice_channel = guild.voice_client.channel
                if len([m for m in voice_channel.members if not m.bot]) == 0:
                    if guild_id not in self.last_member_time:
                        self.last_member_time[guild_id] = time.time()
                    elif time.time() - self.last_member_time[guild_id] > 180:  # 3 minutes
                        await self.disconnect_and_cleanup(guild)
                        continue  # Skip the rest of the loop for this guild
                else:
                    self.last_member_time.pop(guild_id, None)

                if not guild.voice_client.is_playing():
                    if time.time() - self.last_activity[guild_id] > 180:  # 3 minutes
                        await self.disconnect_and_cleanup(guild)
                else:
                    self.reset_activity_timer(guild_id)
            else:
                # If the bot is not in a voice channel, clean up any leftover data
                self.queue.pop(guild_id, None)
                self.current_song.pop(guild_id, None)
                self.last_activity.pop(guild_id, None)
                self.last_member_time.pop(guild_id, None)

    @commands.command()
    async def play(self, ctx, *, query):
        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("You need to be in a voice channel to use this command.")
            return

        try:
            if ctx.voice_client is None:
                await voice_channel.connect()
            else:
                await ctx.voice_client.move_to(voice_channel)
        except asyncio.TimeoutError:
            await ctx.send("Failed to connect to the voice channel. Please try again later.")
            return
        except discord.errors.ClientException as e:
            await ctx.send(f"An error occurred while connecting to the voice channel: {str(e)}")
            return

        # Check if the query is a YouTube or YouTube Music link
        if query.startswith(('https://www.youtube.com/', 'https://youtu.be/', 'https://music.youtube.com/')):
            processing_msg = await ctx.send("Processing YouTube link... This may take a while for large playlists.")
            song_infos = await self.extract_info(query)
            await processing_msg.delete()
        else:
            await ctx.send("Searching for the song... This may take a moment.")
            song_infos = [await search_youtube(query)]

        if not song_infos:
            await ctx.send(f"Failed to process the requested song or playlist: {query}")
            return

        songs_added = 0
        for song_info in song_infos:
            if song_info and 'url' in song_info and 'title' in song_info:
                if ctx.guild.id not in self.queue:
                    self.queue[ctx.guild.id] = []
                self.queue[ctx.guild.id].append(song_info)
                songs_added += 1

        if songs_added == 1:
            await ctx.send(f"Added to queue: {song_infos[0]['title']}")
        elif songs_added > 1:
            await ctx.send(f"Added {songs_added} songs to the queue.")
        else:
            await ctx.send("No valid songs were found.")

        self.reset_activity_timer(ctx.guild.id)
        self.last_member_time.pop(ctx.guild.id, None)

        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    async def play_next(self, ctx):
        self.reset_activity_timer(ctx.guild.id)
        if len(self.queue[ctx.guild.id]) > 0:
            song = self.queue[ctx.guild.id].pop(0)
            self.current_song[ctx.guild.id] = song
            try:
                ctx.voice_client.play(discord.FFmpegPCMAudio(song['url'], before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"), 
                                      after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
                await ctx.send(f"Now playing: {song['title']}")
            except Exception as e:
                await ctx.send(f"An error occurred while playing the song: {str(e)}")
                await self.play_next(ctx)
        else:
            self.current_song[ctx.guild.id] = None
            await ctx.send("Queue is empty. Use .play to add more songs.")

    @commands.command(aliases=['next'])
    async def skip(self, ctx):
        self.reset_activity_timer(ctx.guild.id)
        voice_client = ctx.voice_client
        if voice_client.is_playing():
            voice_client.stop()
            await ctx.send("Skipped the current song.")
        else:
            await ctx.send("No audio is currently playing.")

    @commands.command()
    async def queue(self, ctx):
        self.reset_activity_timer(ctx.guild.id)
        if ctx.guild.id not in self.queue or len(self.queue[ctx.guild.id]) == 0:
            await ctx.send("The queue is empty.")
        else:
            queue_list = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(self.queue[ctx.guild.id])])
            current_song = self.current_song.get(ctx.guild.id)
            if current_song:
                queue_list = f"Now playing: {current_song['title']}\n\nQueue:\n{queue_list}"
            
            # Split the queue into multiple messages if it's too long
            if len(queue_list) > 1900:  # Discord has a 2000 character limit
                parts = []
                while len(queue_list) > 1900:
                    part, queue_list = queue_list[:1900], queue_list[1900:]
                    parts.append(f"```{part}```")
                parts.append(f"```{queue_list}```")
                for part in parts:
                    await ctx.send(part)
            else:
                await ctx.send(f"```{queue_list}```")

    @commands.command()
    async def clear(self, ctx):
        self.reset_activity_timer(ctx.guild.id)
        if ctx.guild.id in self.queue:
            self.queue[ctx.guild.id].clear()
            await ctx.send("Queue cleared.")
        else:
            await ctx.send("The queue is already empty.")

    @commands.command()
    async def stop(self, ctx):
        self.reset_activity_timer(ctx.guild.id)
        voice_client = ctx.voice_client
        if voice_client.is_playing():
            voice_client.stop()
        if ctx.guild.id in self.queue:
            self.queue[ctx.guild.id].clear()
        self.current_song[ctx.guild.id] = None
        await ctx.send("Playback stopped and queue cleared.")

    @commands.command()
    async def leave(self, ctx):
        self.last_activity.pop(ctx.guild.id, None)
        self.last_member_time.pop(ctx.guild.id, None)
        voice_client = ctx.voice_client
        if voice_client.is_connected():
            if ctx.guild.id in self.queue:
                self.queue[ctx.guild.id].clear()
            self.current_song[ctx.guild.id] = None
            await voice_client.disconnect()
            await ctx.send("Disconnected from the voice channel.")
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    async def extract_info(self, url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'no_warnings': True,
            'quiet': True,
            'extract_flat': 'in_playlist',
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                },
                'youtubetab': {
                    'skip': ['dash', 'hls'],
                },
            },
        }
        
        async def extract():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                    if 'entries' in info:
                        # It's a playlist
                        entries = []
                        for entry in info['entries']:
                            try:
                                video_info = await asyncio.to_thread(ydl.extract_info, entry['url'], download=False)
                                entries.append({'url': video_info['url'], 'title': video_info['title']})
                            except Exception as e:
                                print(f"Error extracting info for {entry.get('title', 'unknown')}: {e}")
                        return entries
                    else:
                        # It's a single video
                        return [{'url': info['url'], 'title': info['title']}]
            except Exception as e:
                print(f"Error in extract: {e}")
                return None

        try:
            songs = await asyncio.wait_for(extract(), timeout=300)  # 5 minute timeout for large playlists
            if songs:
                return [song for song in songs if song['url']]  # Filter out any entries without a URL
            print(f"Failed to extract info for URL: {url}")
            return None
        except asyncio.TimeoutError:
            print(f"Timeout while extracting info for URL: {url}")
            return None
        except Exception as e:
            print(f"An error occurred in extract_info: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

async def setup(bot):
    await bot.add_cog(Music(bot))