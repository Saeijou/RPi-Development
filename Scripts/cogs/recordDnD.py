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
import struct
from scipy import signal

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
        self.start_time = None
        self.chunk_size = 50 * 1024 * 1024  # 50MB
        self.chunk_count = 0

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
        self.start_time = datetime.now()
        self.chunk_count = 0

        await ctx.send(f"Recording started. Use '.stoprecord' to stop.")

        # Start recording
        self.voice_client.listen(voice_recv.BasicSink(self.audio_received))

    def audio_received(self, user, data: voice_recv.VoiceData):
        if not self.is_recording:
            return

        audio_data = data.pcm if hasattr(data, 'pcm') else data

        if isinstance(audio_data, bytes):
            pcm_data = audio_data
        elif hasattr(audio_data, 'tobytes'):
            pcm_data = audio_data.tobytes()
        else:
            logger.error(f"Unexpected audio data type: {type(audio_data)}")
            return

        # Convert to numpy array
        pcm_data = np.frombuffer(pcm_data, dtype=np.int16)

        # Noise reduction
        pcm_data = pcm_data.astype(np.float32)
        pcm_data /= 32768.0  # Normalize to [-1, 1]

        # Simple high-pass filter to reduce low-frequency noise
        b, a = signal.butter(10, 300.0/(48000/2), btype='highpass')
        pcm_data = signal.lfilter(b, a, pcm_data)

        # Soft noise gate
        noise_gate = 0.01
        pcm_data[np.abs(pcm_data) < noise_gate] = 0

        # Convert back to int16
        pcm_data = (pcm_data * 32768).astype(np.int16)

        timestamp = (datetime.now() - self.start_time).total_seconds()
        self.audio_buffer.write(struct.pack('d', timestamp))
        self.audio_buffer.write(pcm_data.tobytes())

        if self.audio_buffer.tell() >= self.chunk_size:
            self.save_chunk()

    def save_chunk(self):
        chunk_filename = f"{self.current_audio_filename[:-4]}_{self.chunk_count}.wav"
        with wave.open(chunk_filename, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            audio_data = self.audio_buffer.getvalue()
            # Remove the timestamp data before writing
            audio_data = audio_data[8:]  # 8 bytes for the double timestamp
            wf.writeframes(audio_data)

        self.chunk_count += 1
        self.audio_buffer = io.BytesIO()

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

        self.save_chunk()  # Save any remaining data
        self.combine_chunks()

        await ctx.send(f"Recording saved to {self.current_audio_filename}")

        # Check if the file was created and has content
        if os.path.exists(self.current_audio_filename) and os.path.getsize(self.current_audio_filename) > 0:
            await ctx.send(f"Transcribing {self.current_audio_filename}...")
            try:
                await self.transcribe_audio(ctx)
            except Exception as e:
                await ctx.send(f"Error during transcription: {str(e)}")
                logger.error(f"Error during transcription: {str(e)}")
        else:
            await ctx.send(f"Error: Audio file {self.current_audio_filename} was not created or is empty.")
            logger.error(f"Error: Audio file {self.current_audio_filename} was not created or is empty.")

    def combine_chunks(self):
        with wave.open(self.current_audio_filename, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)

            for i in range(self.chunk_count):
                chunk_filename = f"{self.current_audio_filename[:-4]}_{i}.wav"
                if not self.check_wav_file(chunk_filename):
                    logger.error(f"Chunk file {chunk_filename} is not a valid WAV file")
                    continue
                with wave.open(chunk_filename, 'rb') as chunk_wf:
                    wf.writeframes(chunk_wf.readframes(chunk_wf.getnframes()))
                os.remove(chunk_filename)

        logger.debug(f"Recording saved to {self.current_audio_filename}")
        if not self.check_wav_file(self.current_audio_filename):
            logger.error(f"Combined file {self.current_audio_filename} is not a valid WAV file")

    async def transcribe_audio(self, ctx):
        if not os.path.exists(self.current_audio_filename) or os.path.getsize(self.current_audio_filename) == 0:
            await ctx.send(f"Error: Audio file {self.current_audio_filename} does not exist or is empty.")
            return

        if not self.check_wav_file(self.current_audio_filename):
            await ctx.send(f"Error: {self.current_audio_filename} is not a valid WAV file.")
            return

        recognizer = sr.Recognizer()
        full_transcript = ""

        try:
            with sr.AudioFile(self.current_audio_filename) as source:
                audio = recognizer.record(source)

            try:
                full_transcript = recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                logger.warning("Google Speech Recognition could not understand the audio")
            except sr.RequestError as e:
                logger.error(f"Could not request results from Google Speech Recognition service; {e}")

            self.current_transcript_filename = self.current_audio_filename.replace(".wav", ".txt")
            with open(self.current_transcript_filename, 'w') as f:
                f.write(full_transcript)

            await ctx.send(f"Transcription complete. Saved to '{self.current_transcript_filename}'.")
            logger.debug(f"Transcription complete. Saved to '{self.current_transcript_filename}'.")
        except Exception as e:
            await ctx.send(f"Error during transcription: {str(e)}")
            logger.error(f"Error during transcription: {str(e)}")

    def check_wav_file(self, filename):
        try:
            with wave.open(filename, 'rb') as wf:
                logger.debug(f"WAV file details for {filename}:")
                logger.debug(f"Number of channels: {wf.getnchannels()}")
                logger.debug(f"Sample width: {wf.getsampwidth()}")
                logger.debug(f"Frame rate: {wf.getframerate()}")
                logger.debug(f"Number of frames: {wf.getnframes()}")
                logger.debug(f"Compression type: {wf.getcomptype()}")
                logger.debug(f"Compression name: {wf.getcompname()}")
            return True
        except wave.Error as e:
            logger.error(f"Error reading WAV file {filename}: {str(e)}")
            return False

    async def send_long_message(self, ctx, message):
        chunks = textwrap.wrap(message, 1900)
        for chunk in chunks:
            await ctx.send(f"```{chunk}```")

async def setup(bot):
    await bot.add_cog(DnDRecorder(bot))