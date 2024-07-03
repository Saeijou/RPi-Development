import discord
from discord.ext import commands, voice_recv
import speech_recognition as sr
from datetime import datetime
import os
import textwrap
import configparser
import wave
import io
import logging
import numpy as np

# Use the existing logging configuration from the bot
logger = logging.getLogger(__name__)

class DnDRecorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_recording = False
        self.current_audio_filename = None
        self.current_transcript_filename = None
        self.voice_client = None
        self.audio_buffer = None

        # Read config
        config = configparser.ConfigParser()
        config.read(os.path.expanduser('~/Python/.config'))

        # Get the cogs directory from config
        cogs_dir = config['Paths']['cogs_folder']

        # Set up the recordings directory
        default_recordings_dir = os.path.join(cogs_dir, 'recordings')
        self.output_dir = config.get('Paths', 'recordings_folder', fallback=default_recordings_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        logger.debug(f"Output directory set to: {self.output_dir}")

    @commands.command()
    async def recordDnD(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("You need to be in a voice channel to use this command.")
            return

        if self.is_recording:
            await ctx.send("Already recording. Use '.stoprecord' to stop.")
            return

        try:
            voice_channel = ctx.author.voice.channel
            if ctx.voice_client:
                await ctx.voice_client.move_to(voice_channel)
                self.voice_client = ctx.voice_client
            else:
                self.voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
        except Exception as e:
            await ctx.send(f"Error connecting to voice channel: {str(e)}")
            logger.error(f"Error connecting to voice channel: {str(e)}")
            return

        self.is_recording = True
        logger.debug("Recording started")

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_audio_filename = os.path.join(self.output_dir, f"recorded_audio_{timestamp}.wav")
        self.audio_buffer = io.BytesIO()

        await ctx.send(f"Recording started. Use '.stoprecord' to stop.")

        # Start recording
        self.voice_client.listen(voice_recv.BasicSink(self.audio_received))

    def audio_received(self, user, data: voice_recv.VoiceData):
        if not self.is_recording:
            return

        # Check if data has 'pcm' attribute, otherwise try to use the object directly
        audio_data = data.pcm if hasattr(data, 'pcm') else data

        if isinstance(audio_data, bytes):
            pcm_data = audio_data
        elif hasattr(audio_data, 'tobytes'):
            pcm_data = audio_data.tobytes()
        else:
            logger.error(f"Unexpected audio data type: {type(audio_data)}")
            return

        logger.debug(f"Audio data received from {user}: {len(pcm_data)} bytes")

        # Calculate audio level (this is a simple RMS calculation)
        try:
            audio_samples = np.frombuffer(pcm_data, dtype=np.int16)
            audio_level = np.sqrt(np.mean(np.square(audio_samples)))
            logger.debug(f"Audio level: {audio_level}")
        except Exception as e:
            logger.error(f"Error calculating audio level: {str(e)}")

        # Save raw audio data
        self.audio_buffer.write(pcm_data)

    @commands.command(aliases=['stoprecord'])
    async def stopRecording(self, ctx):
        if not self.is_recording:
            await ctx.send("I'm not currently recording.")
            return

        self.is_recording = False
        logger.debug("Recording stopped")
        if self.voice_client:
            self.voice_client.stop_listening()
            await self.voice_client.disconnect()
            self.voice_client = None

        # Check if any audio data was recorded
        if self.audio_buffer.getbuffer().nbytes == 0:
            await ctx.send("No audio data was recorded. The file is empty.")
            logger.error("No audio data recorded")
            return

        # Save the recorded audio
        with wave.open(self.current_audio_filename, 'wb') as wf:
            wf.setnchannels(2)  # Stereo
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(48000)  # 48kHz
            wf.writeframes(self.audio_buffer.getvalue())

        await ctx.send(f"Recording saved to {self.current_audio_filename}")
        logger.debug(f"Recording saved to {self.current_audio_filename}")

        # Check if the file was created and has content
        if os.path.exists(self.current_audio_filename) and os.path.getsize(self.current_audio_filename) > 0:
            await ctx.send(f"Recording stopped. Transcribing {self.current_audio_filename}...")
            try:
                await self.transcribe_audio(ctx)
            except Exception as e:
                await ctx.send(f"Error during transcription: {str(e)}")
                logger.error(f"Error during transcription: {str(e)}")
        else:
            await ctx.send(f"Error: Audio file {self.current_audio_filename} was not created or is empty.")
            logger.error(f"Error: Audio file {self.current_audio_filename} was not created or is empty.")

    async def transcribe_audio(self, ctx):
        recognizer = sr.Recognizer()
        with sr.AudioFile(self.current_audio_filename) as source:
            audio = recognizer.record(source)

        try:
            transcript = recognizer.recognize_google(audio)
            self.current_transcript_filename = self.current_audio_filename.replace(".wav", ".txt")
            with open(self.current_transcript_filename, 'w') as f:
                f.write(transcript)
            await ctx.send(f"Transcription complete. Saved to '{self.current_transcript_filename}'.")
            logger.debug(f"Transcription complete. Saved to '{self.current_transcript_filename}'.")
        except sr.UnknownValueError:
            await ctx.send("Google Speech Recognition could not understand the audio")
            logger.error("Google Speech Recognition could not understand the audio")
        except sr.RequestError as e:
            await ctx.send(f"Could not request results from Google Speech Recognition service; {e}")
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")

    async def send_long_message(self, ctx, message):
        chunks = textwrap.wrap(message, 1900)
        for chunk in chunks:
            await ctx.send(f"```{chunk}```")

async def setup(bot):
    await bot.add_cog(DnDRecorder(bot))
