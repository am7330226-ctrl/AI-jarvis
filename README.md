# 🤖 J.A.R.V.I.S. — Just A Rather Very Intelligent System

> **An intelligent, real-time AI desktop assistant for Windows featuring Hinglish voice interaction, local Whisper speech recognition, OS automation, safety controls, and a modern Web Dashboard.**

---

## 🌟 Key Features

- 🎙️ **Local Speech-to-Text (STT):** Powered by `faster-whisper` for fast, offline, zero-cost speech recognition.
- 🗣️ **Natural Text-to-Speech (TTS):** Uses Microsoft Neural Voice (`edge-tts` with `hi-IN-MadhurNeural`) for natural Hinglish speech output.
- 🧠 **Multi-LLM Backend:** Connects to **Google Gemini 2.5 Flash**, **Groq (Llama 3.3 70B)**, or **OpenRouter** with function calling and tool execution.
- 💬 **Hinglish Butler Persona:** Responds in witty, concise Hinglish written in Latin script.
- 💻 **Full Windows OS Automation:**
  - Open, close, and switch between desktop applications.
  - System controls: master volume, screen brightness, mute, lock/shutdown.
  - Media playback control: play/pause, next track, previous track.
  - Auto-typing & keyboard shortcut simulation via PyAutoGUI & Keyboard.
  - Web searching and whitelisted shell command execution.
- 🛡️ **Safety & Confirmation Gate:** Protects your system from destructive or dangerous commands (e.g., `rmdir`, `shutdown`, file deletion) using interactive confirmation checks.
- 📊 **Real-time Web Dashboard:** FastAPI WebSocket backend streams live assistant status, transcript updates, tool logs, and system resource telemetry (CPU, RAM) to a React + Vite dashboard.
- 🔑 **Activation Controls:** Hotkey trigger (press **`F9`**) with optional open-source wake-word detection (`openwakeword`).

---

## 📁 Repository Structure

```
AI-jarvis/
├── backend/                  # Python Backend & AI Logic
│   ├── llm/                  # Gemini / Groq / OpenRouter LLM agent & prompt engineering
│   ├── stt/                  # Faster-Whisper local speech recognition engine
│   ├── tts/                  # Edge-TTS engine with voice synthesis customization
│   ├── tools/                # OS tools (App, System, Media, Shell, Typing, Web search)
│   ├── safety/               # Dangerous command pattern detection & confirmation gate
│   ├── wake_word/            # Hotkey & optional wake-word listener (openwakeword/porcupine)
│   ├── config.py             # Configuration & environment variables manager
│   ├── main.py               # Backend main orchestrator
│   └── server.py             # FastAPI & WebSocket server for Dashboard UI
├── frontend/                 # React + Vite Dashboard
│   ├── src/                  # Dashboard components, status indicators, live transcript
│   ├── package.json          # Frontend dependencies & scripts
│   └── vite.config.js        # Vite dev server configuration
├── .env                      # API keys & local environment configuration
├── main.py                   # Root entry point (`python main.py`)
├── setup.bat                 # One-click Windows setup script
├── run_jarvis.bat            # Windows startup script
├── requirements.txt          # Python dependencies
└── pyrightconfig.json        # Python type checking configuration
```

---

## ⚙️ Prerequisites

- **Operating System:** Windows 10 / 11 (recommended)
- **Python:** Python 3.10 or higher
- **Node.js:** Node.js 18+ & npm (required only for running the React Dashboard)
- **Microphone & Speakers:** Working audio input and output devices

---

## 🚀 Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/AI-jarvis.git
cd AI-jarvis
```

### 2. Run Setup Script (Windows)
Run `setup.bat` to automatically create a Python virtual environment (`venv`) and install all required dependencies:

```cmd
setup.bat
```

*Or manually setup in PowerShell / Command Prompt:*
```cmd
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔐 API Key Configuration

Create or edit the `.env` file in the root directory:

```env
# Required: Choose at least one LLM Provider Key

# Google Gemini (Recommended — Free Tier Available)
# Get key: https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Groq (Optional)
# Get key: https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here

# OpenRouter (Optional)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional TTS & Wake-Word Keys
ELEVENLABS_API_KEY=
PORCUPINE_ACCESS_KEY=
```

---

## 🎮 How to Run

### Launching Jarvis Assistant

Run `run_jarvis.bat` (or run via terminal):

```cmd
run_jarvis.bat
```

*Or manually:*
```cmd
venv\Scripts\activate
python -m backend.main
```

### Controls & Usage

- 🎙️ **Voice Interaction:** Press **`F9`** on your keyboard, speak your request, and wait for Jarvis to respond.
- 🧹 **Reset History:** Say *"clear history"* or *"reset context"*.
- ❌ **Shutdown:** Press **`Ctrl+C`** in the terminal or say *"goodbye jarvis"* / *"exit"*.

---

## 🖥️ Launching the Web Dashboard (Frontend)

To launch the real-time React dashboard:

```cmd
cd frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173`. The dashboard will automatically connect to the WebSocket server running on `ws://localhost:8765`.

---

## 🛠️ Configuration & Customization

You can customize assistant parameters in `backend/config.py`:

- **LLM Models:** Change default model names (`GEMINI_MODEL`, `GROQ_MODEL`, `OPENROUTER_MODEL`).
- **TTS Voices:** Change voice (`EDGE_TTS_VOICE`), speech rate (`EDGE_TTS_RATE`), or pitch (`EDGE_TTS_PITCH`).
- **Speech Recognition:** Change Whisper model size (`WHISPER_MODEL_SIZE = "base"`) or compute device (`WHISPER_DEVICE = "cpu"` or `"cuda"`).
- **Hotkeys:** Change trigger key (`TRIGGER_HOTKEY = "f9"`).

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
