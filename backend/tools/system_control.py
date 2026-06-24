"""
System Control Tool
===================
Handles OS-level power management and display controls on Windows.
"""

import ctypes
import subprocess
import logging

logger = logging.getLogger(__name__)

try:
    import screen_brightness_control as sbc
    HAS_SBC = True
except ImportError:
    HAS_SBC = False
    logger.warning("screen-brightness-control not available.")


def lock_screen() -> str:
    """Lock the Windows workstation."""
    logger.info("Locking screen.")
    ctypes.windll.user32.LockWorkStation()
    return "Screen locked."


def sleep_system() -> str:
    """Put the system to sleep."""
    logger.info("Initiating system sleep.")
    subprocess.run(
        ["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"],
        check=False,
    )
    return "Going to sleep. Good night."


def shutdown_system() -> str:
    """Shutdown the computer (requires confirmation before calling)."""
    logger.info("Initiating system shutdown.")
    subprocess.run(["shutdown", "/s", "/t", "5"], check=False)
    return "Shutting down in 5 seconds."


def restart_system() -> str:
    """Restart the computer (requires confirmation before calling)."""
    logger.info("Initiating system restart.")
    subprocess.run(["shutdown", "/r", "/t", "5"], check=False)
    return "Restarting in 5 seconds."


def cancel_shutdown() -> str:
    """Cancel a pending shutdown or restart."""
    subprocess.run(["shutdown", "/a"], check=False)
    logger.info("Shutdown cancelled.")
    return "Shutdown cancelled."


def set_brightness(level: int) -> str:
    """
    Set screen brightness (0–100).
    
    Args:
        level: Brightness percentage.
    
    Returns:
        Status message.
    """
    level = max(0, min(100, int(level)))

    if HAS_SBC:
        try:
            sbc.set_brightness(level)
            logger.info(f"Brightness set to {level}%")
            return f"Screen brightness set to {level} percent."
        except Exception as e:
            logger.error(f"Brightness error: {e}")
            return f"Could not set brightness: {e}"
    
    return "Screen brightness control is not available on this system."


def get_brightness() -> str:
    """Get current screen brightness."""
    if HAS_SBC:
        try:
            level = sbc.get_brightness(display=0)
            if isinstance(level, list):
                level = level[0]
            return f"Current brightness is {level} percent."
        except Exception as e:
            logger.error(f"Get brightness error: {e}")
    return "Unable to retrieve brightness level."
