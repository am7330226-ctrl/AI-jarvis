"""
Safety Sanitizer
================
Provides command sanitization and verbal confirmation for high-risk actions.
All destructive or irreversible commands must pass through this layer.
"""

import logging
import re
import threading
from typing import Callable, Optional

from backend.config import DANGEROUS_COMMAND_PATTERNS, HIGH_RISK_ACTIONS

logger = logging.getLogger(__name__)


class SafetySanitizer:
    """Validates commands and actions before execution."""

    def __init__(self, speak_fn: Callable[[str], None], listen_fn: Callable[[], str]):
        """
        Args:
            speak_fn: Function to speak a message (TTS).
            listen_fn: Function to listen for user response (STT).
        """
        self.speak = speak_fn
        self.listen = listen_fn

    def is_dangerous_command(self, command: str) -> bool:
        """Check if a shell command contains dangerous patterns."""
        cmd_lower = command.lower()
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if pattern.lower() in cmd_lower:
                logger.warning(f"Dangerous command detected: {command!r} (matched: {pattern!r})")
                return True
        return False

    def is_high_risk_action(self, action_description: str) -> bool:
        """Check if an action description matches high-risk keywords."""
        desc_lower = action_description.lower()
        for keyword in HIGH_RISK_ACTIONS:
            if keyword.lower() in desc_lower:
                return True
        return False

    def sanitize_shell_command(self, command: str) -> Optional[str]:
        """
        Sanitize a shell command.
        Returns the command if safe, None if it should be blocked.
        """
        # Remove attempts to chain multiple commands with && or ; or |
        # Allow piping to benign commands only
        dangerous_ops = [" && ", " ; ", "$(", "`", "> /", ">C:\\Windows", ">C:\\System"]
        for op in dangerous_ops:
            if op in command:
                logger.warning(f"Command chaining/redirection blocked: {command!r}")
                return None

        if self.is_dangerous_command(command):
            return None

        return command.strip()

    def require_confirmation(self, action_description: str) -> bool:
        """
        Speak a confirmation request and listen for verbal yes/no.
        
        Returns:
            True if the user confirmed, False if denied or ambiguous.
        """
        prompt = (
            f"This will {action_description}. "
            "Are you sure? Please say yes to confirm or no to cancel."
        )
        logger.info(f"Requesting confirmation for: {action_description}")
        self.speak(prompt)

        # Give a brief pause then listen
        response = self.listen()
        response_lower = response.lower().strip()

        confirmed = any(word in response_lower for word in ["yes", "yeah", "confirm", "do it", "proceed", "sure", "affirmative"])
        denied = any(word in response_lower for word in ["no", "cancel", "stop", "don't", "abort", "negative"])

        if confirmed and not denied:
            logger.info("Action confirmed by user.")
            return True
        else:
            logger.info(f"Action denied (response: {response!r}).")
            self.speak("Action cancelled.")
            return False
