"""
Jarvis — Main Entry Point
==========================
Orchestrates the full voice assistant pipeline:
  Listen (STT) → Think (Gemini) → Act (Tools) → Speak (TTS) → Repeat

Phase 1 & 2: Press F9 to trigger a voice interaction.
Phase 3: Wake word will replace the hotkey.
"""

import logging
import sys
import time
import threading
import psutil

import keyboard

from backend.config import GEMINI_API_KEY, TRIGGER_HOTKEY, WEBSOCKET_HOST, WEBSOCKET_PORT, WAKE_WORD_ENGINE
from backend.stt.whisper_stt import WhisperSTT
from backend.tts.edge_tts_engine import EdgeTTSEngine
from backend.llm.gemini_brain import GeminiBrain
from backend.tools.executor import ToolExecutor
from backend.server import broadcast_event, start_server_in_background

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("jarvis.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("jarvis.main")


class Jarvis:
    """The main Jarvis assistant controller."""

    def __init__(self):
        # Validate API key
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
            logger.error("Please set your GEMINI_API_KEY in backend/config.py or .env before running.")
            sys.exit(1)

        logger.info("Initializing JARVIS systems...")

        self.stt = WhisperSTT()
        self.tts = EdgeTTSEngine()
        
        # Tool executor needs speak/listen callbacks for confirmation prompts
        self.tool_executor = ToolExecutor(
            speak_fn=self._speak,
            listen_fn=self._listen,
        )
        
        # Status callback pushes state to the dashboard in real-time
        self.brain = GeminiBrain(
            tool_executor=self.tool_executor,
            status_callback=self._on_status_change,
        )

        self._active = False
        self._listening = False
        self._current_state = "idle"

        # Initialize the configured trigger listener
        self.wake_word_mode = False
        try:
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
                raise ValueError("Wake word engine not enabled.")
        except Exception as e:
            from backend.wake_word.listener import HotkeyListener
            logger.warning(f"Wake word setup failed ({e}). Falling back to hotkey [{TRIGGER_HOTKEY.upper()}]...")
            self.listener = HotkeyListener(
                hotkey=TRIGGER_HOTKEY,
                on_trigger=self._on_trigger,
            )
            self.wake_word_mode = False

        logger.info("All systems online.")

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _speak(self, text: str) -> None:
        """Speak a response and broadcast to dashboard."""
        if not text:
            return
        broadcast_event("transcript", role="jarvis", text=text)
        self.tts.speak(text, status_callback=self._on_status_change)

    def _listen(self) -> str:
        """Record and transcribe a user utterance."""
        text = self.stt.listen_and_transcribe(status_callback=self._on_status_change)
        if text:
            broadcast_event("transcript", role="user", text=text)
        return text

    def _on_status_change(self, state: str) -> None:
        """Broadcast state changes to the dashboard."""
        self._current_state = state
        broadcast_event("status", state=state)
        logger.debug(f"State: {state}")

    # ─── System metrics broadcaster ───────────────────────────────────────────

    def _broadcast_system_metrics(self) -> None:
        """Periodically push CPU/RAM stats to the dashboard."""
        while True:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                broadcast_event("system", cpu=cpu, ram=ram)
            except Exception:
                pass
            time.sleep(3)

    # ─── Core interaction loop ────────────────────────────────────────────────

    def handle_interaction(self) -> None:
        """Perform one full listen → think → speak cycle."""
        if self._listening:
            logger.info("Already listening, ignoring hotkey.")
            return

        self._listening = True

        try:
            # If Jarvis is speaking, interrupt first
            if self.tts.is_speaking():
                self.tts.interrupt()
                time.sleep(0.3)

            # Listen
            user_text = self._listen()

            if not user_text:
                self._speak("I didn't catch that. Could you repeat?")
                return

            # Special commands
            if any(cmd in user_text.lower() for cmd in ["goodbye", "shut down jarvis", "exit jarvis", "stop jarvis"]):
                self._speak("Goodbye. JARVIS going offline.")
                self.stop()
                return

            if any(cmd in user_text.lower() for cmd in ["clear history", "reset memory", "forget everything"]):
                self.brain.reset()
                self._speak("Conversation history cleared. Starting fresh.")
                return

            # Think & respond
            response = self.brain.think(user_text)
            if response:
                self._speak(response)

        except Exception as e:
            logger.error(f"Interaction error: {e}", exc_info=True)
            self._speak("I encountered an unexpected error. Please try again.")
        finally:
            self._listening = False
            self._on_status_change("idle")

    # ─── Start / Stop ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the Jarvis assistant and start the listener."""
        self._active = True

        # Start WebSocket dashboard server
        start_server_in_background()
        logger.info(f"Dashboard available at http://localhost:5173 (start frontend separately)")
        logger.info(f"WebSocket at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws")

        # Start system metrics broadcaster
        metrics_thread = threading.Thread(
            target=self._broadcast_system_metrics,
            daemon=True,
            name="JarvisMetrics",
        )
        metrics_thread.start()

        # Start trigger listener
        self.listener.start()

        # Welcome message depending on trigger mode
        time.sleep(1)
        if getattr(self, "wake_word_mode", False):
            welcome_text = "JARVIS online. All systems are operational. Say Hey Jarvis to give me a command, sir."
        else:
            welcome_text = f"JARVIS online. All systems are operational. Press {TRIGGER_HOTKEY.upper()} to give me a command, sir."
        self._speak(welcome_text)

        # Keep main thread alive
        try:
            while self._active:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def _on_trigger(self) -> None:
        """Handle trigger (hotkey or wake word) in a separate thread to avoid blocking."""
        thread = threading.Thread(
            target=self.handle_interaction,
            daemon=True,
            name="JarvisInteraction",
        )
        thread.start()

    def stop(self) -> None:
        """Gracefully stop the Jarvis assistant."""
        logger.info("Shutting down JARVIS...")
        self._active = False
        self.listener.stop()
        self.tts.interrupt()
        sys.exit(0)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
    +--------------------------------------------------+
    |                                                  |
    |        J.A.R.V.I.S  Voice Assistant              |
    |    Just A Rather Very Intelligent System         |
    |                                                  |
    +--------------------------------------------------+
    |  * Press F9 to speak a command                   |
    |  * Press Ctrl+C to quit                          |
    |  * Dashboard: http://localhost:5173              |
    |                                                  |
    +--------------------------------------------------+
    """)

    jarvis = Jarvis()
    jarvis.start()
