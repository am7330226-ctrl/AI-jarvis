"""
Typing & Keyboard Tool
======================
Emulates keyboard input — typing text, pressing hotkeys, and shortcuts.
Uses pyautogui for reliable cross-application text input.
"""

import logging
import time
import pyautogui

logger = logging.getLogger(__name__)

# Safety: disable pyautogui failsafe (move mouse to top-left to abort)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # Small delay between keystrokes for reliability


def type_text(text: str, interval: float = 0.03) -> str:
    """
    Type text at the current cursor position.
    
    Args:
        text: The text to type.
        interval: Delay between keystrokes in seconds.
    
    Returns:
        Status message.
    """
    logger.info(f"Typing text: {text[:50]}{'...' if len(text) > 50 else ''!r}")
    # Small pause to let user switch focus if needed
    time.sleep(0.3)
    pyautogui.write(text, interval=interval)
    return f"Typed: {text[:40]}{'...' if len(text) > 40 else ''}"


def press_hotkey(*keys: str) -> str:
    """
    Press a keyboard hotkey combination.
    
    Args:
        *keys: Key names to press simultaneously (e.g., 'ctrl', 'c').
    
    Returns:
        Status message.
    
    Examples:
        press_hotkey('ctrl', 'c')   # Copy
        press_hotkey('alt', 'tab')  # Switch window
        press_hotkey('win', 'd')    # Show desktop
    """
    logger.info(f"Pressing hotkey: {' + '.join(keys)}")
    pyautogui.hotkey(*keys)
    return f"Pressed {' + '.join(keys)}."


def press_key(key: str) -> str:
    """
    Press a single key.
    
    Args:
        key: Key name (e.g., 'enter', 'escape', 'tab', 'f5').
    
    Returns:
        Status message.
    """
    logger.info(f"Pressing key: {key!r}")
    pyautogui.press(key)
    return f"Pressed {key}."


# ─── Common shortcut helpers ───────────────────────────────────────────────────

def copy() -> str:
    """Simulate Ctrl+C (copy)."""
    return press_hotkey("ctrl", "c")

def paste() -> str:
    """Simulate Ctrl+V (paste)."""
    return press_hotkey("ctrl", "v")

def undo() -> str:
    """Simulate Ctrl+Z (undo)."""
    return press_hotkey("ctrl", "z")

def select_all() -> str:
    """Simulate Ctrl+A (select all)."""
    return press_hotkey("ctrl", "a")

def save() -> str:
    """Simulate Ctrl+S (save)."""
    return press_hotkey("ctrl", "s")

def new_tab() -> str:
    """Simulate Ctrl+T (new tab)."""
    return press_hotkey("ctrl", "t")

def close_tab() -> str:
    """Simulate Ctrl+W (close tab)."""
    return press_hotkey("ctrl", "w")

def show_desktop() -> str:
    """Show Windows desktop."""
    return press_hotkey("win", "d")

def take_screenshot() -> str:
    """Take a screenshot using Win+Shift+S (Windows Snipping Tool)."""
    press_hotkey("win", "shift", "s")
    return "Screenshot tool opened."
