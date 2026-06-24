"""
Jarvis LLM Agent — Groq Backend
=================================
Uses Groq's ultra-fast inference API with LLaMA 3.3 70B for:
  - Conversational reasoning with tool/function calling
  - Maintaining rolling conversation history
  - OS automation via registered tools
  - Safety enforcement via the sanitizer
"""

import json
import logging
import re
from typing import Callable, Optional

# pyrefly: ignore [missing-import]
from groq import Groq, BadRequestError, RateLimitError

from backend.config import GROQ_API_KEY, GROQ_MODEL, MAX_HISTORY_TURNS, JARVIS_SYSTEM_PROMPT
from backend.tools import app_control, media_control, system_control, typing_tool
from backend.safety.sanitizer import SafetySanitizer

logger = logging.getLogger(__name__)


# ─── Tool Definitions (OpenAI-compatible JSON Schema) ─────────────────────────

TOOLS = [
    # ── Application Control ──────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Launch an application by its friendly name (e.g., 'Chrome', 'Notepad', 'Spotify').",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Friendly name of the application to open."}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description": "Close a running application by its name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the application to close."}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_to_window",
            "description": "Bring a window to the foreground by partial title match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Partial window title to search for."}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_apps",
            "description": "List all notable applications currently running on the system.",
            "parameters": {"type": "object", "properties": {}},
        },
    },

    # ── Volume / Media Control ───────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set the system audio volume to a specific percentage (0 to 100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume percentage from 0 to 100."}
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_volume",
            "description": "Get the current system volume level.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mute_toggle",
            "description": "Toggle system audio mute on or off.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume_up",
            "description": "Increase the system volume by a given percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "integer", "description": "Percentage to increase volume by (default 10)."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume_down",
            "description": "Decrease the system volume by a given percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "integer", "description": "Percentage to decrease volume by (default 10)."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_pause",
            "description": "Simulate the media play/pause key to control music or video playback.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "next_track",
            "description": "Skip to the next media track.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "previous_track",
            "description": "Go back to the previous media track.",
            "parameters": {"type": "object", "properties": {}},
        },
    },

    # ── System Control ───────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Lock the Windows workstation screen immediately.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_system",
            "description": "Put the computer into sleep mode.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_system",
            "description": "Shut down the computer. ALWAYS call require_confirmation first.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restart_system",
            "description": "Restart the computer. ALWAYS call require_confirmation first.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_shutdown",
            "description": "Cancel a pending system shutdown or restart.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set screen brightness to a percentage (0 to 100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Brightness percentage from 0 to 100."}
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_brightness",
            "description": "Get the current screen brightness level.",
            "parameters": {"type": "object", "properties": {}},
        },
    },

    # ── Keyboard / Typing ────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text at the current cursor position in any active window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to type."}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_hotkey",
            "description": "Press a keyboard shortcut combination (e.g., Ctrl+C, Alt+Tab, Win+D).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key names to press simultaneously, e.g. ['ctrl', 'c'].",
                    }
                },
                "required": ["keys"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a single keyboard key (e.g., 'enter', 'escape', 'tab', 'f5').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name to press."}
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Open the Windows Snipping Tool to take a screenshot.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_desktop",
            "description": "Minimize all windows and show the Windows desktop.",
            "parameters": {"type": "object", "properties": {}},
        },
    },

    # ── Safety ───────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "require_confirmation",
            "description": (
                "Ask the user to verbally confirm a dangerous or irreversible action. "
                "MUST be called before shutdown, restart, delete, or any destructive operation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action_description": {
                        "type": "string",
                        "description": "Plain English description of the action (e.g., 'shut down your computer').",
                    }
                },
                "required": ["action_description"],
            },
        },
    },
]


# ─── Tool Executor ─────────────────────────────────────────────────────────────

class ToolExecutor:
    """Maps Groq function call names to actual Python functions."""

    def __init__(self, sanitizer: SafetySanitizer):
        self.sanitizer = sanitizer
        self._registry = {
            # App control
            "open_application":   lambda a: app_control.open_application(a["name"]),
            "close_application":  lambda a: app_control.close_application(a["name"]),
            "switch_to_window":   lambda a: app_control.switch_to_window(a["name"]),
            "list_running_apps":  lambda a: app_control.list_running_apps(),
            # Media
            "set_volume":         lambda a: media_control.set_volume(a["level"]),
            "get_volume":         lambda a: media_control.get_volume(),
            "mute_toggle":        lambda a: media_control.mute_toggle(),
            "volume_up":          lambda a: media_control.volume_up(a.get("amount", 10)),
            "volume_down":        lambda a: media_control.volume_down(a.get("amount", 10)),
            "play_pause":         lambda a: media_control.play_pause(),
            "next_track":         lambda a: media_control.next_track(),
            "previous_track":     lambda a: media_control.previous_track(),
            # System
            "lock_screen":        lambda a: system_control.lock_screen(),
            "sleep_system":       lambda a: system_control.sleep_system(),
            "shutdown_system":    lambda a: system_control.shutdown_system(),
            "restart_system":     lambda a: system_control.restart_system(),
            "cancel_shutdown":    lambda a: system_control.cancel_shutdown(),
            "set_brightness":     lambda a: system_control.set_brightness(a["level"]),
            "get_brightness":     lambda a: system_control.get_brightness(),
            # Keyboard
            "type_text":          lambda a: typing_tool.type_text(a["text"]),
            "press_hotkey":       lambda a: typing_tool.press_hotkey(*a["keys"]),
            "press_key":          lambda a: typing_tool.press_key(a["key"]),
            "take_screenshot":    lambda a: typing_tool.take_screenshot(),
            "show_desktop":       lambda a: typing_tool.show_desktop(),
            # Safety
            "require_confirmation": lambda a: str(
                self.sanitizer.require_confirmation(a["action_description"])
            ),
        }

    def execute(self, name: str, args: dict) -> str:
        handler = self._registry.get(name)
        if handler is None:
            logger.warning(f"Unknown tool: {name!r}")
            return f"Tool '{name}' is not available."
        try:
            logger.info(f"Executing: {name}({args})")
            result = handler(args)
            logger.info(f"Result: {result!r}")
            return str(result)
        except Exception as e:
            logger.error(f"Tool error [{name}]: {e}", exc_info=True)
            return f"Error executing {name}: {e}"


# ─── Main Agent ────────────────────────────────────────────────────────────────

class JarvisAgent:
    """
    Groq-powered conversational agent for Jarvis.
    Uses LLaMA 3.3 70B with function calling via Groq's API.
    """

    def __init__(self, speak_fn: Callable[[str], None], listen_fn: Callable[[], str]):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.sanitizer = SafetySanitizer(speak_fn=speak_fn, listen_fn=listen_fn)
        self.tool_executor = ToolExecutor(sanitizer=self.sanitizer)

        # System prompt as the first message
        self.history: list[dict] = [
            {"role": "system", "content": JARVIS_SYSTEM_PROMPT}
        ]

        logger.info(f"JarvisAgent initialized with Groq model: {GROQ_MODEL}")

    # ─── XML Fallback Parser ──────────────────────────────────────────────────

    def _parse_xml_tool_calls(self, failed_generation: str) -> list[tuple[str, dict]]:
        """
        Parse Llama's native XML-format tool calls as a fallback.
        llama-3.3-70b-versatile sometimes generates:
            <function=open_application{"name": "Notepad"}</function>
        instead of the expected OpenAI JSON tool call format.
        """
        results = []
        # Match: <function=FUNCNAME{...JSON...} or <function=FUNCNAME>{...JSON...}
        pattern = r'<function=(\w+)>?(\{.*?\})'
        for match in re.finditer(pattern, failed_generation, re.DOTALL):
            name = match.group(1)
            try:
                args = json.loads(match.group(2))
            except (json.JSONDecodeError, ValueError):
                args = {}
            logger.info(f"XML fallback parsed: {name}({args})")
            results.append((name, args))
        return results

    def _trim_history(self):
        """Keep history within limits, always preserving the system prompt."""
        max_messages = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_messages + 1:  # +1 for system prompt
            self.history = [self.history[0]] + self.history[-(max_messages):]

    def process(self, user_input: str, status_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Process a user utterance through the agentic loop.

        Args:
            user_input: Transcribed text from the user.
            status_callback: Optional callable(str) for UI status updates.

        Returns:
            Jarvis's final spoken response as a string.
        """
        if not user_input.strip():
            return ""

        logger.info(f"User: {user_input!r}")
        self.history.append({"role": "user", "content": user_input})

        if status_callback:
            status_callback("thinking")

        MAX_ITERATIONS = 6

        for iteration in range(MAX_ITERATIONS):
            try:
                response = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=self.history,
                    tools=TOOLS,
                    tool_choice="auto",
                    parallel_tool_calls=False,
                    temperature=0.3,
                    max_tokens=512,
                )
            except RateLimitError as e:
                logger.warning(f"Groq Rate Limit exceeded: {e}")
                self.history.pop()  # Remove failed user message
                return "Groq rate limit exceed ho gaya hai, boss. Please thodi der baad try karein."
            except BadRequestError as e:
                # Check if it's a tool_use_failed — model used XML format instead of JSON
                error_body = getattr(e, 'body', {}) or {}
                error_info = error_body.get('error', {})
                if error_info.get('code') == 'tool_use_failed':
                    failed_gen = error_info.get('failed_generation', '')
                    logger.warning(f"tool_use_failed — attempting XML fallback parse.")
                    parsed = self._parse_xml_tool_calls(failed_gen)
                    if parsed:
                        if status_callback:
                            status_callback("executing")
                        results = []
                        for tool_name, tool_args in parsed:
                            result = self.tool_executor.execute(tool_name, tool_args)
                            results.append(result)
                        final_response = " ".join(results)
                        self.history.append({"role": "assistant", "content": final_response})
                        self._trim_history()
                        return final_response
                # Not a tool_use_failed or couldn't parse — fall through
                logger.error(f"Groq API error: {e}", exc_info=True)
                self.history.pop()
                return "I'm having trouble reaching my intelligence core right now. Please try again."
            except Exception as e:
                logger.error(f"Groq API error: {e}", exc_info=True)
                self.history.pop()  # Remove failed user message
                return "I'm having trouble reaching my intelligence core right now. Please try again."

            message = response.choices[0].message
            tool_calls = message.tool_calls

            if tool_calls:
                # Append the assistant's tool-call message to history
                self.history.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                })

                if status_callback:
                    status_callback("executing")

                # Execute each tool and collect results
                for tc in tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    result = self.tool_executor.execute(tool_name, tool_args)

                    # Append tool result to history
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                if status_callback:
                    status_callback("thinking")

                # Loop back to get the model's verbal response
                continue

            else:
                # Final text response — no more tool calls
                final_text = (message.content or "").strip()
                logger.info(f"Jarvis (raw): {final_text!r}")

                parsed_xml = self._parse_xml_tool_calls(final_text)
                if parsed_xml:
                    logger.info("Found XML tool calls in text response content. Executing...")
                    # Clean the XML tags from text so Jarvis doesn't speak them
                    cleaned_text = re.sub(r'<function=\w+>?\{.*?\}(</function>)?', '', final_text).strip()
                    if not cleaned_text:
                        cleaned_text = "Ji, main kar deta hoon, boss."
                    
                    if status_callback:
                        status_callback("executing")

                    for tool_name, tool_args in parsed_xml:
                        self.tool_executor.execute(tool_name, tool_args)

                    logger.info(f"Jarvis (clean): {cleaned_text!r}")
                    self.history.append({"role": "assistant", "content": cleaned_text})
                    self._trim_history()
                    return cleaned_text
                else:
                    self.history.append({"role": "assistant", "content": final_text})
                    self._trim_history()
                    return final_text

        logger.warning("Agentic loop exhausted — returning generic response.")
        return "I've completed the requested actions."

    def clear_history(self):
        """Reset conversation history, keeping only the system prompt."""
        self.history = [self.history[0]]
        logger.info("Conversation history cleared.")
