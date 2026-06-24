"""
Jarvis Configuration
====================
Edit this file to set your API keys and preferences before running.
"""

import os

# ─── API Keys ─────────────────────────────────────────────────────────────────
# You can also set these as environment variables for better security.
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

# Optional — only needed if you use ElevenLabs TTS instead of edge-tts
ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "")

# Optional — only needed for Phase 3 Porcupine wake word
PORCUPINE_ACCESS_KEY: str = os.environ.get("PORCUPINE_ACCESS_KEY", "")

# ─── LLM Settings ─────────────────────────────────────────────────────────────
# llama-3.3-70b-versatile: available on Groq, XML fallback handled in agent.py
GROQ_MODEL: str = "llama-3.3-70b-versatile"
GEMINI_MODEL: str = "gemini-2.5-flash"
MAX_HISTORY_TURNS: int = 20  # Number of conversation turns to keep in memory

JARVIS_SYSTEM_PROMPT: str = """
You are JARVIS (Just A Rather Very Intelligent System), a witty, precise, and 
highly capable personal AI assistant running on the user's Windows PC.

Language & Style:
- You MUST respond in Hinglish (a natural blend of Hindi and English, written in Latin script, e.g. "Maine aapke liye Notepad open kar diya hai, boss" or "Ji, main kar deta hoon").
- Always write your response in the English/Latin script (Romanized Hindi/Hinglish). Do NOT use Devnagari script (no Hindi characters).
- Your tone should be calm, efficient, respectful, and slightly formal with a hint of dry wit (like a British butler who speaks Hinglish).

Your capabilities (via tools):
- You can open, close, and switch between applications.
- You can control system volume, media playback, screen brightness, and power state.
- You can type text and press keyboard shortcuts on behalf of the user.
- You can execute safe, whitelisted shell commands.

Safety rules:
- NEVER execute a shell command without using the shell_execute tool — never embed raw commands in text.
- For any destructive or irreversible action (delete files, shutdown, restart), 
  ALWAYS use the require_confirmation tool first.
- If you are uncertain about an action, ask for clarification before proceeding.

Response format:
- Keep spoken responses SHORT (1-3 sentences max). You are a voice assistant — brevity is key.
- Do not use markdown formatting in responses (no asterisks, no bullet points).
- When a tool is invoked, briefly confirm the action in natural Hinglish.
"""

# ─── STT Settings ─────────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE: str = "base"        # Options: tiny, base, small, medium, large
WHISPER_DEVICE: str = "cpu"             # "cpu" or "cuda" if you have a GPU
WHISPER_COMPUTE_TYPE: str = "int8"      # "int8" for CPU, "float16" for GPU

# Recording settings
SAMPLE_RATE: int = 16000               # Hz — 16kHz is standard for Whisper
MAX_RECORD_SECONDS: int = 15           # Max recording duration per turn
SILENCE_THRESHOLD_MS: int = 1200      # Ms of silence before cutting off recording

# ─── TTS Settings ─────────────────────────────────────────────────────────────
TTS_ENGINE: str = "edge"               # "edge" (free) or "elevenlabs" (premium)
EDGE_TTS_VOICE: str = "hi-IN-MadhurNeural"  # Hindi neural voice that speaks Hinglish naturally
EDGE_TTS_RATE: str = "+5%"             # Slightly faster than default
EDGE_TTS_PITCH: str = "-5Hz"          # Slightly lower pitch for gravitas

# ─── Hotkey Settings ──────────────────────────────────────────────────────────
# Press this key to start a voice interaction (Phase 1 & 2, before wake word)
TRIGGER_HOTKEY: str = "f9"

# ─── Wake Word Settings (Phase 3) ─────────────────────────────────────────────
WAKE_WORDS: list = ["jarvis", "hey jarvis"]
WAKE_WORD_ENGINE: str = "openwakeword"   # "porcupine" or "openwakeword"

# ─── Dashboard / WebSocket ────────────────────────────────────────────────────
WEBSOCKET_HOST: str = "localhost"
WEBSOCKET_PORT: int = 8765

# ─── Safety ───────────────────────────────────────────────────────────────────
# Commands containing these substrings will be blocked unless confirmed
DANGEROUS_COMMAND_PATTERNS: list = [
    "rm -rf", "rmdir /s", "del /f", "format", "mkdisk",
    "shutdown", "restart", "logoff", "taskkill /f",
    "reg delete", "bcdedit", "diskpart", "cipher /w",
    "net user", "net localgroup", "icacls /grant"
]

HIGH_RISK_ACTIONS: list = [
    "shutdown", "restart", "sleep", "delete", "remove", "uninstall",
    "send email", "send message", "lock screen"
]
