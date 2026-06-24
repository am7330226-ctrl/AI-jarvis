"""
JARVIS — Main Entry Point
==========================
Wires all components together and starts the assistant loop.

Usage:
    python main.py

Controls:
    - Press F9 (or configured hotkey) to speak to Jarvis
    - Press Ctrl+C in the terminal to shut down gracefully
    - Say "clear history" to reset the conversation context
    - Say "exit" or "goodbye jarvis" to shut down the assistant
"""

import logging
import sys
import os
import threading
import time

# ─── Logging Setup (do this first) ───────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("jarvis.log", encoding="utf-8"),
    ],
)
# Quiet noisy third-party loggers
logging.getLogger("faster_whisper").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("pygame").setLevel(logging.WARNING)

logger = logging.getLogger("jarvis.main")


# ─── Config Validation ────────────────────────────────────────────────────────
def _validate_config():
    from backend.config import GROQ_API_KEY
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith("gsk_"):
        logger.critical(
            "\n" + "=" * 60 +
            "\n  ERROR: GROQ_API_KEY is not set or invalid!\n"
            "  Edit backend/config.py and set your Groq API key.\n"
            "  Get a free key at: https://console.groq.com/keys\n" +
            "=" * 60
        )
        sys.exit(1)


# ─── Jarvis Core Class ────────────────────────────────────────────────────────
class Jarvis:
    """
    The main Jarvis orchestrator.
    Manages the STT → LLM → TTS pipeline and wake-word triggering.
    """

    def __init__(self):
        self._status = "initializing"
        self._interaction_lock = threading.Lock()

        logger.info("=" * 60)
        logger.info("  Initializing J.A.R.V.I.S. — Just A Rather Very Intelligent System")
        logger.info("=" * 60)

        # Lazy imports (avoid loading heavy models until needed)
        from backend.stt.whisper_stt import WhisperSTT
        from backend.tts.edge_tts_engine import EdgeTTSEngine
        from backend.llm.agent import JarvisAgent
        from backend.config import TRIGGER_HOTKEY, WAKE_WORD_ENGINE

        logger.info("Loading Speech-to-Text engine...")
        self.stt = WhisperSTT()

        logger.info("Loading Text-to-Speech engine...")
        self.tts = EdgeTTSEngine()

        logger.info("Initializing AI agent...")
        self.agent = JarvisAgent(
            speak_fn=self.speak,
            listen_fn=self.listen,
        )

        # Initialize the configured trigger listener
        self.wake_word_mode = False
        if WAKE_WORD_ENGINE == "openwakeword":
            from backend.wake_word.listener import OpenWakeWordListener
            logger.info("Setting up OpenWakeWord wake word listener...")
            self.listener = OpenWakeWordListener(
                on_trigger=self._on_trigger,
            )
            self.wake_word_mode = True
        elif WAKE_WORD_ENGINE == "porcupine":
            from backend.wake_word.listener import PorcupineListener
            logger.info("Setting up Porcupine wake word listener...")
            self.listener = PorcupineListener(
                on_trigger=self._on_trigger,
            )
            self.wake_word_mode = True
        else:
            from backend.wake_word.listener import HotkeyListener
            logger.info(f"Setting up hotkey listener [{TRIGGER_HOTKEY.upper()}]...")
            self.listener = HotkeyListener(
                hotkey=TRIGGER_HOTKEY,
                on_trigger=self._on_trigger,
            )

        self._running = False
        self._status = "idle"
        logger.info("[OK] All systems nominal. Jarvis is ready.\n")

    # ─── Public Interface ─────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Speak text through TTS with status updates."""
        if not text:
            return
        self._set_status("speaking")
        self.tts.speak(text, status_callback=self._set_status)

    def listen(self) -> str:
        """Listen for microphone input and return transcribed text."""
        self._set_status("listening")
        return self.stt.listen_and_transcribe(status_callback=self._set_status)

    # ─── Core Interaction Flow ────────────────────────────────────────────────

    def _on_trigger(self):
        """Called when the hotkey is pressed. Starts a voice interaction."""
        # Prevent overlapping interactions
        if not self._interaction_lock.acquire(blocking=False):
            logger.info("Already in an interaction — ignoring trigger.")
            return

        try:
            self._run_interaction()
        finally:
            self._interaction_lock.release()

    def _run_interaction(self):
        """Run a single full interaction: listen → think → speak."""
        self.tts.interrupt()  # Stop any ongoing speech

        # Brief audio cue: play a subtle activation sound
        self._play_activation_sound()

        # Listen for user input
        user_text = self.listen()

        if not user_text.strip():
            logger.info("No speech detected — returning to idle.")
            self._set_status("idle")
            return

        logger.info(f"Heard: {user_text!r}")

        # Handle meta-commands locally (no LLM call needed)
        if self._handle_meta_commands(user_text):
            return

        # Send to Gemini agent
        self._set_status("thinking")
        response = self.agent.process(user_text, status_callback=self._set_status)

        if response:
            self.speak(response)

        self._set_status("idle")

    def _handle_meta_commands(self, text: str) -> bool:
        """
        Handle special commands that don't go to the LLM.
        Returns True if the command was handled locally.
        """
        text_lower = text.lower().strip()

        if any(kw in text_lower for kw in ["clear history", "reset memory", "forget everything"]):
            self.agent.clear_history()
            self.speak("Memory cleared. Fresh start.")
            return True

        if any(kw in text_lower for kw in ["goodbye jarvis", "shut down jarvis", "exit jarvis", "stop jarvis"]):
            self.speak("Goodbye. Shutting down now.")
            logger.info("User requested shutdown.")
            self._running = False
            return True

        if any(kw in text_lower for kw in ["what can you do", "help", "your capabilities"]):
            help_text = (
                "I can open and close applications, control your volume and media playback, "
                "adjust screen brightness, lock your screen, type text for you, "
                "press keyboard shortcuts, and answer your questions. "
                "Just ask me anything."
            )
            self.speak(help_text)
            return True

        return False

    # ─── Status & Audio Helpers ───────────────────────────────────────────────

    def _set_status(self, status: str) -> None:
        """Update internal status and print to console."""
        self._status = status
        icons = {
            "idle":         "  [IDLE]      ",
            "listening":    "  [LISTENING] ",
            "processing":   "  [PROCESSING]",
            "thinking":     "  [THINKING]  ",
            "executing":    "  [EXECUTING] ",
            "speaking":     "  [SPEAKING]  ",
            "initializing": "  [INIT]      ",
        }
        label = icons.get(status, f"[{status.upper()}]")
        print(f"\r  Status: {label}              ", end="", flush=True)

    def _play_activation_sound(self):
        """Play a short beep/chime to signal that Jarvis is listening."""
        try:
            import winsound
            # Double beep: 880Hz for 80ms, then 1100Hz for 80ms
            winsound.Beep(880, 80)
            winsound.Beep(1100, 80)
        except Exception:
            pass  # Non-critical — silently skip if winsound fails

    # ─── Main Loop ────────────────────────────────────────────────────────────

    def run(self):
        """Start Jarvis and block until shutdown is requested."""
        self._running = True
        self.listener.start()

        print("\n" + "=" * 60)
        print("  J.A.R.V.I.S. is online")
        if getattr(self, "wake_word_mode", False):
            print("  Say 'Hey Jarvis' to activate  |  Ctrl+C to exit")
        else:
            from backend.config import TRIGGER_HOTKEY
            print(f"  Press [{TRIGGER_HOTKEY.upper()}] to speak  |  Ctrl+C to exit")
        print("=" * 60 + "\n")

        # Startup greeting
        self.speak("Systems online. How can I assist you?")
        self._set_status("idle")

        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n")
            logger.info("Ctrl+C received — shutting down.")
        finally:
            self._shutdown()

    def _shutdown(self):
        """Gracefully stop all subsystems."""
        logger.info("Shutting down Jarvis...")
        self._running = False
        self.listener.stop()
        self.tts.interrupt()
        print("\n  Jarvis offline. Goodbye.\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _validate_config()

    try:
        jarvis = Jarvis()
        jarvis.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
