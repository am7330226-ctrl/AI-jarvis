"""
Tool Executor
=============
Central dispatcher that maps Gemini tool call names to Python functions.
Also handles the safety confirmation layer for high-risk actions.
"""

import logging
from typing import Callable, Optional

from backend.tools import app_control, media_control, system_control, typing_tool, web_search, shell_executor
from backend.safety.sanitizer import SafetySanitizer

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Routes Gemini tool calls to the correct Python function."""

    def __init__(self, speak_fn: Callable, listen_fn: Callable):
        self.sanitizer = SafetySanitizer(speak_fn, listen_fn)

        # Actions that require verbal confirmation before executing
        self._high_risk_actions = {
            "sleep_system": "put your computer to sleep",
            "shutdown_system": "shut down your computer",
            "restart_system": "restart your computer",
        }

        # Map of tool name → callable
        self._registry = {
            # App control
            "open_application": lambda args: app_control.open_application(args["name"]),
            "close_application": lambda args: app_control.close_application(args["name"]),
            "switch_to_window": lambda args: app_control.switch_to_window(args["name"]),
            "list_running_apps": lambda args: app_control.list_running_apps(),
            # Volume
            "set_volume": lambda args: media_control.set_volume(args["level"]),
            "get_volume": lambda args: media_control.get_volume(),
            "mute_toggle": lambda args: media_control.mute_toggle(),
            "volume_up": lambda args: media_control.volume_up(args.get("amount", 10)),
            "volume_down": lambda args: media_control.volume_down(args.get("amount", 10)),
            # Media
            "play_pause": lambda args: media_control.play_pause(),
            "next_track": lambda args: media_control.next_track(),
            "previous_track": lambda args: media_control.previous_track(),
            # System
            "lock_screen": lambda args: system_control.lock_screen(),
            "set_brightness": lambda args: system_control.set_brightness(args["level"]),
            "get_brightness": lambda args: system_control.get_brightness(),
            "sleep_system": lambda args: system_control.sleep_system(),
            "shutdown_system": lambda args: system_control.shutdown_system(),
            "restart_system": lambda args: system_control.restart_system(),
            # Keyboard
            "type_text": lambda args: typing_tool.type_text(args["text"]),
            "press_hotkey": lambda args: typing_tool.press_hotkey(*args["keys"]),
            "take_screenshot": lambda args: typing_tool.take_screenshot(),
            # Web
            "search_web": lambda args: web_search.search_web(args["query"], args.get("engine", "duckduckgo")),
            "get_weather": lambda args: web_search.get_weather(args["city"]),
            "open_url": lambda args: web_search.open_url(args["url"]),
            "get_time_and_date": lambda args: web_search.get_time_and_date(),
            # Shell
            "execute_command": lambda args: self._safe_execute_command(args["command"]),
        }

    def execute(self, tool_name: str, args: dict) -> str:
        """
        Execute a tool call by name.

        Args:
            tool_name: Name of the tool to call (matches Gemini FunctionDeclaration name).
            args: Arguments dictionary from Gemini.

        Returns:
            Result string to feed back to Gemini.
        """
        handler = self._registry.get(tool_name)

        if not handler:
            logger.warning(f"Unknown tool called: {tool_name!r}")
            return f"Unknown tool: {tool_name}"

        # Check if this action needs verbal confirmation
        if tool_name in self._high_risk_actions:
            action_desc = self._high_risk_actions[tool_name]
            confirmed = self.sanitizer.require_confirmation(action_desc)
            if not confirmed:
                return "Action was cancelled by the user."

        try:
            return handler(args)
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
            return f"Error executing {tool_name}: {e}"

    def _safe_execute_command(self, command: str) -> str:
        """Run command through sanitizer before execution."""
        safe_cmd = self.sanitizer.sanitize_shell_command(command)
        if safe_cmd is None:
            return "That command is not permitted for safety reasons."
        return shell_executor.execute_command(safe_cmd)
