"""
Text-to-Speech Engine
=====================
Uses Microsoft's edge-tts (free, neural quality) for audio synthesis.
Audio playback uses miniaudio (MP3 decode) + sounddevice (PCM output),
which work on all Python versions including 3.14+.

The GuyNeural voice provides a deep, authoritative Jarvis-like tone.
Supports interruption — if the user starts speaking, TTS is stopped.
"""

import asyncio
import logging
import tempfile
import os
import threading
import time

import edge_tts
import miniaudio
import sounddevice as sd
import numpy as np

from backend.config import (
    EDGE_TTS_VOICE,
    EDGE_TTS_RATE,
    EDGE_TTS_PITCH,
)

logger = logging.getLogger(__name__)


class EdgeTTSEngine:
    """Synthesizes text to speech using edge-tts, decodes with miniaudio, plays via sounddevice."""

    def __init__(self):
        self._playing = False
        self._stop_event = threading.Event()
        logger.info(f"TTS engine initialized with voice: {EDGE_TTS_VOICE}")

    def speak(self, text: str, status_callback=None) -> None:
        """
        Synthesize and play speech synchronously.

        Args:
            text: The text to speak.
            status_callback: Optional callable(str) for status updates.
        """
        if not text or not text.strip():
            return

        if status_callback:
            status_callback("speaking")

        logger.info(f"Speaking: {text[:80]}{'...' if len(text) > 80 else ''}")
        self._stop_event.clear()
        self._playing = True

        try:
            asyncio.run(self._synthesize_and_play(text))
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
        finally:
            self._playing = False
            if status_callback:
                status_callback("idle")

    async def _synthesize_and_play(self, text: str) -> None:
        """Async: synthesize MP3 via edge-tts, then decode and play."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=EDGE_TTS_VOICE,
            rate=EDGE_TTS_RATE,
            pitch=EDGE_TTS_PITCH,
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            await communicate.save(tmp_path)
            self._play_audio(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _play_audio(self, audio_path: str) -> None:
        """Decode MP3 with miniaudio and play PCM via sounddevice."""
        try:
            # Decode the MP3 to raw 16-bit signed PCM
            decoded = miniaudio.decode_file(
                audio_path,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=1,
                sample_rate=22050,
            )
            audio_data = np.frombuffer(decoded.samples, dtype=np.int16)

            # Play using sounddevice (non-blocking, we poll for stop)
            sd.play(audio_data, samplerate=decoded.sample_rate)

            # Poll until done or interrupted
            while sd.get_stream().active:
                if self._stop_event.is_set():
                    sd.stop()
                    logger.info("TTS interrupted by user.")
                    return
                time.sleep(0.05)

            sd.wait()

        except Exception as e:
            logger.error(f"Audio playback error: {e}", exc_info=True)
            sd.stop()

    def interrupt(self) -> None:
        """Signal the TTS engine to stop speaking immediately."""
        if self._playing:
            logger.info("Interrupting TTS playback.")
            self._stop_event.set()
            sd.stop()
            self._playing = False

    def is_speaking(self) -> bool:
        """Returns True if TTS is currently playing."""
        return self._playing
