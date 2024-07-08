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
import asyncio
from pydub import AudioSegment
from pydub.effects import normalize
from pydub.silence import split_on_silence

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DnDRecorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_recording = False
        self.current_audio_filename = None
        self.current_transcript_filename = None
        self.voice_client = None
        self.audio_buffer = io.BytesIO()
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
    async def record(self, ctx):
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

    def audio_received(self, user, data):
        if not self.is_recording:
            return

        pcm_data = data.pcm if hasattr(data, 'pcm') else data

        timestamp = (datetime.now() - self.start_time).total_seconds()
        self.audio_buffer.write(struct.pack('d', timestamp))
        self.audio_buffer.write(pcm_data)

        if self.audio_buffer.tell() >= self.chunk_size:
            self.save_chunk()

    def save_chunk(self):
        chunk_filename = f"{self.current_audio_filename[:-4]}_{self.chunk_count}.wav"
        with wave.open(chunk_filename, 'wb') as wf:
            wf.setnchannels(2)  # Stereo
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(48000)  # 48 kHz (Discord's native sample rate)
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

        if os.path.exists(self.current_audio_filename) and os.path.getsize(self.current_audio_filename) > 0:
            await ctx.send("Processing audio...")
            processed_audio_filename = self.current_audio_filename.replace('.wav', '_processed.wav')
            
            try:
                logger.debug(f"Attempting to process audio file: {self.current_audio_filename}")
                success = await self.process_audio(self.current_audio_filename, processed_audio_filename)
                
                if success and os.path.exists(processed_audio_filename) and os.path.getsize(processed_audio_filename) > 0:
                    self.current_audio_filename = processed_audio_filename
                    await ctx.send("Audio processing completed successfully.")
                    logger.info("Audio processing completed successfully.")
                else:
                    await ctx.send("Audio processing failed. Using original audio.")
                    logger.warning("Audio processing failed or produced empty file.")
            except Exception as e:
                await ctx.send(f"Error during audio processing: {str(e)}. Using original audio.")
                logger.error(f"Error during audio processing: {str(e)}", exc_info=True)

            await ctx.send(f"Transcribing {self.current_audio_filename}...")
            try:
                await self.transcribe_audio(ctx)
            except Exception as e:
                await ctx.send(f"Error during transcription: {str(e)}")
                logger.error(f"Error during transcription: {str(e)}", exc_info=True)
        else:
            await ctx.send(f"Error: Audio file {self.current_audio_filename} was not created or is empty.")
            logger.error(f"Error: Audio file {self.current_audio_filename} was not created or is empty.")

    def combine_chunks(self):
        combined = AudioSegment.empty()
        for i in range(self.chunk_count):
            chunk_filename = f"{self.current_audio_filename[:-4]}_{i}.wav"
            if not self.check_wav_file(chunk_filename):
                logger.error(f"Chunk file {chunk_filename} is not a valid WAV file")
                continue
            chunk = AudioSegment.from_wav(chunk_filename)
            combined += chunk
            os.remove(chunk_filename)

        combined.export(self.current_audio_filename, format="wav")
        logger.debug(f"Recording saved to {self.current_audio_filename}")
        if not self.check_wav_file(self.current_audio_filename):
            logger.error(f"Combined file {self.current_audio_filename} is not a valid WAV file")

    async def process_audio(self, input_file, output_file):
        logger.info(f"Starting audio processing for {input_file}")
        try:
            # Load the audio file
            audio = AudioSegment.from_wav(input_file)
            logger.info(f"Loaded audio file: duration={len(audio)}ms, channels={audio.channels}")

            # Increase volume by 50%
            audio = audio + 6  # Increasing by 6dB is roughly equivalent to 150% volume
            logger.info("Increased volume by 50%")

            # Normalize audio
            audio = normalize(audio)
            logger.info("Normalized audio")

            # Export the processed audio
            audio.export(output_file, format="wav")
            logger.info(f"Exported processed audio to {output_file}")

            return True
        except Exception as e:
            logger.error(f"Error during audio processing: {str(e)}", exc_info=True)
            return False

    async def transcribe_audio(self, ctx):
        if not os.path.exists(self.current_audio_filename) or os.path.getsize(self.current_audio_filename) == 0:
            await ctx.send(f"Error: Audio file {self.current_audio_filename} does not exist or is empty.")
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300  # Adjust this value as needed

        full_transcript = ""

        try:
            with wave.open(self.current_audio_filename, 'rb') as wf:
                frame_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                n_frames = wf.getnframes()

                logger.debug(f"Audio file details: rate={frame_rate}, channels={n_channels}, width={sample_width}, frames={n_frames}")

                chunk_duration = 60  # 60 seconds
                chunk_size = int(chunk_duration * frame_rate * n_channels * sample_width)

                for i in range(0, n_frames, chunk_size):
                    wf.setpos(i)
                    chunk = wf.readframes(min(chunk_size, n_frames - i))

                    with io.BytesIO(chunk) as chunk_io:
                        with wave.open(chunk_io, 'wb') as chunk_wf:
                            chunk_wf.setnchannels(n_channels)
                            chunk_wf.setsampwidth(sample_width)
                            chunk_wf.setframerate(frame_rate)
                            chunk_wf.writeframes(chunk)

                        chunk_io.seek(0)
                        with sr.AudioFile(chunk_io) as source:
                            audio = recognizer.record(source)

                    try:
                        # Try Google first, then fall back to Sphinx if it fails
                        try:
                            transcript = recognizer.recognize_google(audio)
                        except sr.UnknownValueError:
                            transcript = recognizer.recognize_sphinx(audio)
                        full_transcript += transcript + " "
                        logger.debug(f"Transcribed chunk {i//chunk_size + 1}: {transcript}")
                        await ctx.send(f"Transcribed chunk {i//chunk_size + 1}")
                    except sr.UnknownValueError:
                        logger.warning(f"Could not understand audio in chunk {i//chunk_size + 1}")
                    except sr.RequestError as e:
                        logger.error(f"Error in chunk {i//chunk_size + 1}: {str(e)}")

            if not full_transcript:
                await ctx.send("Transcription failed: No speech could be recognized in the audio.")
                return

            self.current_transcript_filename = self.current_audio_filename.replace(".wav", ".txt")
            with open(self.current_transcript_filename, 'w') as f:
                f.write(full_transcript)

            await ctx.send(f"Transcription complete. Saved to '{self.current_transcript_filename}'.")
            logger.info(f"Transcription complete. Saved to '{self.current_transcript_filename}'.")
        except Exception as e:
            await ctx.send(f"Error during transcription: {str(e)}")
            logger.error(f"Error during transcription: {str(e)}", exc_info=True)

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