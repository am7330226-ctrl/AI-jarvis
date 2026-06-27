"""
Gemini LLM Brain
================
The core reasoning engine for Jarvis.
Uses Gemini 2.5 Flash with native tool-calling to orchestrate all actions.
Maintains multi-turn conversation history for contextual responses.
"""

import logging
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.tools.executor import ToolExecutor

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
import google.api_core.exceptions

from backend.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    JARVIS_SYSTEM_PROMPT,
    MAX_HISTORY_TURNS,
)

logger = logging.getLogger(__name__)

# ─── Tool Function Declarations (Gemini Schema) ───────────────────────────────

TOOL_DECLARATIONS = [
    # ── App Control ──
    FunctionDeclaration(
        name="open_application",
        description="Launch or open an application, file, document, or folder path on the user's computer.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the app (e.g., 'Chrome'), or an absolute file path (e.g., 'C:\\Users\\PW\\Documents\\report.pdf')."}
            },
            "required": ["name"],
        },
    ),
    FunctionDeclaration(
        name="close_application",
        description="Close or terminate a running application.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the application to close."}
            },
            "required": ["name"],
        },
    ),
    FunctionDeclaration(
        name="switch_to_window",
        description="Bring a specific application window to the foreground.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Part of the window title to search for."}
            },
            "required": ["name"],
        },
    ),
    FunctionDeclaration(
        name="list_running_apps",
        description="Get a list of currently running applications.",
        parameters={"type": "object", "properties": {}},
    ),
    # ── Volume / Media ──
    FunctionDeclaration(
        name="set_volume",
        description="Set the system volume to a specific percentage.",
        parameters={
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Volume level from 0 to 100."}
            },
            "required": ["level"],
        },
    ),
    FunctionDeclaration(
        name="get_volume",
        description="Get the current system volume level.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="mute_toggle",
        description="Toggle the system audio mute on or off.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="volume_up",
        description="Increase system volume.",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "Amount to increase by (default 10)."}
            },
        },
    ),
    FunctionDeclaration(
        name="volume_down",
        description="Decrease system volume.",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "Amount to decrease by (default 10)."}
            },
        },
    ),
    FunctionDeclaration(
        name="play_pause",
        description="Play or pause the currently playing media.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="next_track",
        description="Skip to the next media track.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="previous_track",
        description="Go to the previous media track.",
        parameters={"type": "object", "properties": {}},
    ),
    # ── System Control ──
    FunctionDeclaration(
        name="lock_screen",
        description="Lock the Windows workstation screen.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="set_brightness",
        description="Set the screen brightness to a specific percentage.",
        parameters={
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Brightness level from 0 to 100."}
            },
            "required": ["level"],
        },
    ),
    FunctionDeclaration(
        name="get_brightness",
        description="Get the current screen brightness level.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="sleep_system",
        description="Put the computer into sleep mode. REQUIRES USER CONFIRMATION.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="shutdown_system",
        description="Shutdown the computer. REQUIRES USER CONFIRMATION.",
        parameters={"type": "object", "properties": {}},
    ),
    FunctionDeclaration(
        name="restart_system",
        description="Restart the computer. REQUIRES USER CONFIRMATION.",
        parameters={"type": "object", "properties": {}},
    ),
    # ── Typing / Keyboard ──
    FunctionDeclaration(
        name="type_text",
        description="Type text at the current cursor position in any application.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to type."}
            },
            "required": ["text"],
        },
    ),
    FunctionDeclaration(
        name="press_hotkey",
        description="Press a keyboard shortcut combination (e.g., Ctrl+C, Alt+Tab, Win+D).",
        parameters={
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key names to press simultaneously (e.g., ['ctrl', 'c']).",
                }
            },
            "required": ["keys"],
        },
    ),
    FunctionDeclaration(
        name="take_screenshot",
        description="Take a screenshot using the Windows Snipping Tool.",
        parameters={"type": "object", "properties": {}},
    ),
    # ── Web / Info ──
    FunctionDeclaration(
        name="search_web",
        description="Search the web using DuckDuckGo or Google and open results in the browser.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "engine": {"type": "string", "description": "Search engine: 'duckduckgo', 'google', 'bing', or 'youtube'. Defaults to 'duckduckgo'."},
            },
            "required": ["query"],
        },
    ),
    FunctionDeclaration(
        name="get_weather",
        description="Get the current weather conditions for a city.",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name to get weather for."}
            },
            "required": ["city"],
        },
    ),
    FunctionDeclaration(
        name="open_url",
        description="Open a specific URL in the default browser.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to open."}
            },
            "required": ["url"],
        },
    ),
    FunctionDeclaration(
        name="get_time_and_date",
        description="Get the current time and date.",
        parameters={"type": "object", "properties": {}},
    ),
    # ── Shell ──
    FunctionDeclaration(
        name="execute_command",
        description="Execute a safe, whitelisted PowerShell or terminal command and return the output.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute."}
            },
            "required": ["command"],
        },
    ),
]

JARVIS_TOOLS = Tool(function_declarations=TOOL_DECLARATIONS)


class GeminiBrain:
    """Jarvis reasoning core powered by Gemini with multi-turn history."""

    def __init__(self, tool_executor: "ToolExecutor", status_callback: Optional[Callable] = None):
        """
        Args:
            tool_executor: Object that dispatches tool calls to the correct function.
            status_callback: Optional callable(str) for broadcasting state changes.
        """
        genai.configure(api_key=GEMINI_API_KEY)
        
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=JARVIS_SYSTEM_PROMPT,
            tools=[JARVIS_TOOLS],
        )
        
        self.chat = self.model.start_chat(history=[])
        self.tool_executor = tool_executor
        self.status_callback = status_callback
        self._turn_count = 0
        
        logger.info(f"Gemini brain initialized: {GEMINI_MODEL}")

    def _update_status(self, state: str) -> None:
        if self.status_callback:
            self.status_callback(state)

    def think(self, user_input: str) -> str:
        """
        Process a user message and return Jarvis's response.
        Handles multi-turn tool-calling loops automatically.
        
        Args:
            user_input: Transcribed user speech.
        
        Returns:
            Final text response from Jarvis.
        """
        if not user_input.strip():
            return ""

        logger.info(f"User: {user_input}")
        self._update_status("thinking")
        self._turn_count += 1

        # Trim history if needed
        if self._turn_count > MAX_HISTORY_TURNS:
            self._trim_history()

        try:
            response = self.chat.send_message(user_input)
            final_text = self._process_response(response)
            logger.info(f"Jarvis: {final_text}")
            return final_text

        except google.api_core.exceptions.ResourceExhausted:
            logger.warning("Gemini API rate limit exceeded (429).")
            return "Boss, API ki rate limit cross ho gayi hai. Thodi der baad try kijiye."
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return "I encountered an error communicating with my AI core. Please try again."

    def _process_response(self, response) -> str:
        """Process a Gemini response, handling tool calls recursively."""
        # Check for tool calls
        tool_calls = []
        
        for part in response.parts:
            if hasattr(part, "function_call") and part.function_call.name:
                tool_calls.append(part.function_call)

        if not tool_calls:
            # Pure text response
            try:
                return response.text.strip()
            except ValueError:
                # Occurs if Gemini returned no parts (empty response)
                return ""

        # Execute all tool calls and collect results
        tool_results = []
        
        for fc in tool_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            
            logger.info(f"Tool call: {name}({args})")
            self._update_status(f"executing:{name}")

            result = self.tool_executor.execute(name, args)
            logger.info(f"Tool result: {result!r}")

            tool_results.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=name,
                        response={"result": result},
                    )
                )
            )

        # Send all tool results back to Gemini for a natural language response
        follow_up = self.chat.send_message(tool_results)
        return self._process_response(follow_up)

    def _trim_history(self) -> None:
        """Trim the oldest conversation turns to stay within token limits."""
        history = self.chat.history
        if len(history) > MAX_HISTORY_TURNS * 2:
            # Keep system context + recent turns, remove oldest
            self.chat.history = history[-(MAX_HISTORY_TURNS * 2):]
            logger.info("Conversation history trimmed.")

    def reset(self) -> None:
        """Clear conversation history and start fresh."""
        self.chat = self.model.start_chat(history=[])
        self._turn_count = 0
        logger.info("Conversation history cleared.")
