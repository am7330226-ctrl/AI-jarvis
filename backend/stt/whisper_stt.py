"""
Speech-to-Text Engine
=====================
Uses faster-whisper for local, offline transcription.
Records from microphone until silence is detected using a simple
RMS energy-based VAD — no native compilation required (pure numpy).
"""

import queue
import threading
import tempfile
import os
import logging
import numpy as np
import sounddevice as sd
import soundfile as sf

from faster_whisper import WhisperModel

from backend.config import (
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    SAMPLE_RATE,
    MAX_RECORD_SECONDS,
    SILENCE_THRESHOLD_MS,
)

logger = logging.getLogger(__name__)

# ─── Energy VAD Threshold ─────────────────────────────────────────────────────
# RMS level (0–32768 scale) above which a frame is considered speech.
# Increase if Jarvis triggers on background noise; decrease if it misses quiet voices.
DEFAULT_ENERGY_THRESHOLD: int = 250


class WhisperSTT:
    """Handles microphone recording with energy VAD and Whisper transcription."""

    def __init__(self):
        logger.info(f"Loading Whisper model: {WHISPER_MODEL_SIZE} on {WHISPER_DEVICE}")
        self.model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper STT engine ready.")
        
        # Initialize and calibrate energy threshold
        self.energy_threshold = DEFAULT_ENERGY_THRESHOLD
        try:
            self.calibrate_threshold()
        except Exception as e:
            logger.warning(f"Failed to calibrate energy threshold: {e}. Using default {DEFAULT_ENERGY_THRESHOLD}")

    def calibrate_threshold(self):
        """Record 300ms of silence to determine ambient noise floor and set threshold."""
        logger.info("Calibrating microphone ambient noise level...")
        duration = 0.3  # seconds
        samples = int(SAMPLE_RATE * duration)
        
        # Record a short block of ambient sound
        recording = sd.rec(samples, samplerate=SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()
        
        # Calculate RMS
        rms_val = self._rms(recording)
        # Set threshold to 2x ambient noise, bounded between 150 and 800
        self.energy_threshold = max(150, min(800, int(rms_val * 2.0)))
        logger.info(f"Ambient noise RMS: {rms_val:.1f}. Speech threshold set to: {self.energy_threshold}")

    # ─── VAD ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _rms(frame: np.ndarray) -> float:
        """Root-mean-square energy of a 16-bit PCM frame."""
        return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))

    def _is_speech(self, frame: np.ndarray) -> bool:
        """Returns True if the frame's energy is above the speech threshold."""
        return self._rms(frame) > self.energy_threshold

    # ─── Recording ────────────────────────────────────────────────────────────

    def listen_and_transcribe(self, status_callback=None) -> str:
        """
        Record from the microphone until silence, then transcribe with Whisper.

        Args:
            status_callback: Optional callable(str) for status updates.

        Returns:
            Transcribed text string (empty string if nothing detected).
        """
        if status_callback:
            status_callback("listening")

        logger.info("Listening... (speak now)")

        # Audio frame parameters
        frame_duration_ms = 30
        frame_samples = int(SAMPLE_RATE * frame_duration_ms / 1000)
        silence_frames_needed = int(SILENCE_THRESHOLD_MS / frame_duration_ms)
        max_frames = int((MAX_RECORD_SECONDS * 1000) / frame_duration_ms)

        audio_buffer: list[np.ndarray] = []
        silence_counter = 0
        speech_detected = False
        total_frames = 0

        audio_queue: queue.Queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio status: {status}")
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=frame_samples,
            callback=callback,
        ):
            while total_frames < max_frames:
                try:
                    frame = audio_queue.get(timeout=1.0)
                except queue.Empty:
                    break

                is_speech = self._is_speech(frame)

                if is_speech:
                    speech_detected = True
                    silence_counter = 0
                    audio_buffer.append(frame)
                elif speech_detected:
                    # After speech starts, count silence
                    silence_counter += 1
                    audio_buffer.append(frame)
                    if silence_counter >= silence_frames_needed:
                        logger.info("Silence detected — stopping recording.")
                        break

                total_frames += 1

        if not speech_detected or len(audio_buffer) == 0:
            logger.info("No speech detected.")
            if status_callback:
                status_callback("idle")
            return ""

        if status_callback:
            status_callback("processing")

        logger.info(f"Recording complete. Transcribing {len(audio_buffer)} frames...")

        # Concatenate frames and write to a temp WAV
        audio_data = np.concatenate(audio_buffer, axis=0).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            sf.write(tmp_path, audio_data, SAMPLE_RATE, subtype="PCM_16")
            segments, _ = self.model.transcribe(
                tmp_path,
                language="en",
                beam_size=5,
                vad_filter=False,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
        finally:
            os.unlink(tmp_path)

        logger.info(f"Transcribed: {text!r}")

        if status_callback:
            status_callback("thinking")

        return text
