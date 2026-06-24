"""
Shell Command Executor
======================
Executes whitelisted PowerShell commands safely.
All commands pass through the safety sanitizer before execution.
"""

import subprocess
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Strict whitelist: only these command prefixes are permitted
WHITELISTED_PREFIXES: list = [
    "dir", "ls", "echo", "type", "cat",
    "ipconfig", "ping", "tracert", "netstat",
    "systeminfo", "tasklist", "get-process",
    "get-childitem", "get-content", "get-item",
    "get-date", "get-location",
    "mkdir", "new-item",
    "copy", "cp", "move", "mv",
    "rename-item",
    "start-process",
    "python", "pip",
    "git status", "git log", "git diff",
    "npm", "node",
    "code",
    "where", "which",
    "cls", "clear",
]

TIMEOUT_SECONDS: int = 15


def execute_command(command: str) -> str:
    """
    Execute a whitelisted PowerShell command and return its output.
    
    Args:
        command: The shell command to execute.
    
    Returns:
        Combined stdout + stderr output as a string.
    """
    if not _is_whitelisted(command):
        logger.warning(f"Command blocked by whitelist: {command!r}")
        return (
            f"I'm not permitted to run that command. "
            f"For safety, I can only execute a limited set of commands. "
            f"The command '{command[:60]}' is not on my approved list."
        )

    logger.info(f"Executing: {command!r}")

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            encoding="utf-8",
            errors="replace",
        )

        output = result.stdout.strip()
        errors = result.stderr.strip()

        if result.returncode != 0 and errors:
            logger.warning(f"Command stderr: {errors}")
            return f"Command completed with errors: {errors[:200]}"

        if not output:
            return "Command executed successfully with no output."

        # Truncate very long outputs
        if len(output) > 800:
            output = output[:800] + "\n... (output truncated)"

        return output

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {command!r}")
        return f"The command timed out after {TIMEOUT_SECONDS} seconds."
    except FileNotFoundError:
        return "PowerShell is not available on this system."
    except Exception as e:
        logger.error(f"Shell execution error: {e}")
        return f"An error occurred while executing the command: {e}"


def _is_whitelisted(command: str) -> bool:
    """Check if a command starts with a whitelisted prefix."""
    cmd_lower = command.lower().strip()
    for prefix in WHITELISTED_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            return True
    return False
