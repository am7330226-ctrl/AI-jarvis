"""
Wake Word / Hotkey Listener
============================
Phase 1 & 2: Listens for an F9 hotkey press to trigger a voice interaction.
Phase 3 (optional): Can switch to Porcupine or OpenWakeWord for always-on
                    wake-word detection without needing a keypress.

Design:
  - Runs in a background daemon thread so the main loop stays non-blocking.
  - Fires a callback when activation is detected.
  - Supports graceful start/stop.
"""

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HotkeyListener:
    """
    Listens for a keyboard hotkey (default: F9) and calls a callback.
    Runs in a background daemon thread — completely non-blocking.
    """

    def __init__(self, hotkey: str, on_trigger: Callable[[], None]):
        """
        Args:
            hotkey: Key name to listen for (e.g., 'f9').
            on_trigger: Callback invoked when the hotkey is pressed.
        """
        self.hotkey = hotkey.lower()
        self.on_trigger = on_trigger
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cooldown_seconds = 1.0  # Prevent double-trigger
        self._last_trigger_time = 0.0

    def start(self):
        """Start listening for the hotkey in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("HotkeyListener is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_loop,
            name="HotkeyListener",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"HotkeyListener started — press [{self.hotkey.upper()}] to activate Jarvis.")

    def stop(self):
        """Stop the hotkey listener."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("HotkeyListener stopped.")

    def _listen_loop(self):
        """Background loop that polls for the hotkey."""
        try:
            import keyboard  # imported here to allow graceful ImportError handling
        except ImportError:
            logger.error("'keyboard' package not installed. Run: pip install keyboard")
            return

        logger.debug(f"Polling for hotkey: [{self.hotkey.upper()}]")

        while not self._stop_event.is_set():
            try:
                if keyboard.is_pressed(self.hotkey):
                    now = time.monotonic()
                    if now - self._last_trigger_time >= self._cooldown_seconds:
                        self._last_trigger_time = now
                        logger.info(f"Hotkey [{self.hotkey.upper()}] detected — triggering Jarvis.")
                        try:
                            self.on_trigger()
                        except Exception as e:
                            logger.error(f"on_trigger callback error: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Hotkey polling error: {e}", exc_info=True)

            time.sleep(0.05)  # 50ms poll — low CPU, fast enough response


# ─── Optional: Porcupine wake-word wrapper ────────────────────────────────────

class PorcupineListener:
    """
    Always-on wake word listener using Picovoice Porcupine.
    Requires: pip install pvporcupine sounddevice
    and a free Picovoice access key set in config.py.
    """

    def __init__(self, on_trigger: Callable[[], None]):
        self.on_trigger = on_trigger
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="PorcupineListener",
            daemon=True,
        )
        self._thread.start()
        logger.info("Porcupine wake-word listener started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _run(self):
        try:
            import pvporcupine
            import sounddevice as sd
            import numpy as np
            from backend.config import PORCUPINE_ACCESS_KEY
        except ImportError as e:
            logger.error(f"Porcupine dependencies missing: {e}. Falling back to hotkey mode.")
            return

        try:
            porcupine = pvporcupine.create(
                access_key=PORCUPINE_ACCESS_KEY,
                keywords=["jarvis"],
            )
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            return

        frame_length = porcupine.frame_length
        sample_rate = porcupine.sample_rate

        logger.info(f"Porcupine initialized. Frame length: {frame_length}, Sample rate: {sample_rate}")

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                blocksize=frame_length,
            ) as stream:
                while not self._stop_event.is_set():
                    pcm, _ = stream.read(frame_length)
                    pcm = pcm.flatten().tolist()
                    result = porcupine.process(pcm)
                    if result >= 0:
                        logger.info("Wake word 'Jarvis' detected!")
                        try:
                            self.on_trigger()
                        except Exception as e:
                            logger.error(f"on_trigger error: {e}", exc_info=True)
        finally:
            porcupine.delete()
            logger.info("Porcupine listener stopped.")


# ─── Free & Local: OpenWakeWord wrapper ───────────────────────────────────────

class OpenWakeWordListener:
    """
    Always-on wake word listener using OpenWakeWord (fully free, local, no keys).
    Requires: pip install openwakeword sounddevice numpy onnxruntime
    """

    def __init__(self, on_trigger: Callable[[], None], threshold: float = 0.5):
        self.on_trigger = on_trigger
        self.threshold = threshold
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start the wake word listener in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("OpenWakeWordListener is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="OpenWakeWordListener",
            daemon=True,
        )
        self._thread.start()
        logger.info("OpenWakeWordListener started. Say 'Hey Jarvis' to activate.")

    def stop(self):
        """Stop the wake word listener."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        logger.info("OpenWakeWordListener stopped.")

    def _run(self):
        try:
            from openwakeword.model import Model
            import sounddevice as sd
            import numpy as np
        except ImportError as e:
            logger.error(f"OpenWakeWord dependencies missing: {e}. Cannot run wake-word.")
            return

        try:
            # Initialize model with ONNX engine
            model = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx",
            )
            # Find the exact key for the hey_jarvis model
            model_key = next((k for k in model.models.keys() if "hey_jarvis" in k), "hey_jarvis")
            logger.info(f"OpenWakeWord initialized. Active model key: {model_key!r}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenWakeWord model: {e}", exc_info=True)
            return

        chunk_size = 1280  # 80ms at 16kHz
        sample_rate = 16000

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                blocksize=chunk_size,
            ) as stream:
                while not self._stop_event.is_set():
                    # Read block of frames (returns numpy array)
                    audio_chunk, overflowed = stream.read(chunk_size)
                    if overflowed:
                        logger.warning("Audio input stream overflowed.")

                    # Flatten to 1D array
                    pcm = audio_chunk.flatten()
                    
                    # Get prediction scores
                    prediction = model.predict(pcm)
                    
                    # Get score for our model
                    score = prediction.get(model_key, 0.0)
                    if score >= self.threshold:
                        logger.info(f"Wake word detected! (Score: {score:.2f})")
                        try:
                            self.on_trigger()
                        except Exception as e:
                            logger.error(f"on_trigger callback error: {e}", exc_info=True)
                            
        except Exception as e:
            logger.error(f"Error in OpenWakeWord input stream: {e}", exc_info=True)
        finally:
            logger.info("OpenWakeWord listener loop exited.")
