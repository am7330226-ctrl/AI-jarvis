"""
Application Control Tool
========================
Handles launching, closing, and switching to applications on Windows.
"""

import subprocess
import logging
import psutil

try:
    import win32gui
    import win32con
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logging.warning("pywin32 not available — window switching will be limited.")

logger = logging.getLogger(__name__)

# Map of friendly names to executable paths / commands
APP_ALIASES: dict = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "vscode": "code.exe",
    "visual studio code": "code.exe",
    "paint": "mspaint.exe",
    "snipping tool": "snippingtool.exe",
    "clock": "ms-clock:",
}


import os

def open_application(name: str) -> str:
    """
    Launch an application, file, folder, or document by name or path.
    
    Args:
        name: Friendly name, executable name, or absolute file path.
    
    Returns:
        Status message string.
    """
    name_lower = name.lower().strip()
    executable = APP_ALIASES.get(name_lower, name)

    logger.info(f"Opening application/file: {name!r} -> {executable!r}")

    try:
        if hasattr(os, 'startfile'):
            # os.startfile acts exactly like double-clicking a file in Windows.
            # It opens executables, files with default apps, and URLs.
            os.startfile(executable)
        else:
            if executable.startswith("ms-"):
                # Handle Windows URI protocol links (ms-settings:, ms-clock:, etc.)
                subprocess.Popen(["cmd", "/c", "start", "", executable], shell=False)
            else:
                subprocess.Popen(executable, shell=True)
        return f"Opened {name}."
    except FileNotFoundError:
        logger.error(f"Target not found: {executable!r}")
        return f"I couldn't find '{name}'. If it's a specific file, I might need the full path."
    except Exception as e:
        logger.error(f"Error opening {executable!r}: {e}")
        return f"Failed to open {name}: {e}"


def close_application(name: str) -> str:
    """
    Close a running application by process name or friendly name.
    
    Args:
        name: Process name (e.g., 'notepad.exe') or friendly name.
    
    Returns:
        Status message string.
    """
    name_lower = name.lower().strip()
    executable = APP_ALIASES.get(name_lower, name)

    # Normalize: ensure .exe suffix for matching
    if not executable.endswith(".exe") and "." not in executable:
        executable += ".exe"

    executable_lower = executable.lower()
    killed_count = 0

    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == executable_lower:
                proc.terminate()
                killed_count += 1
                logger.info(f"Terminated PID {proc.info['pid']} ({proc.info['name']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed_count > 0:
        return f"Closed {name}."
    else:
        return f"I couldn't find a running instance of '{name}'."


def switch_to_window(name: str) -> str:
    """
    Bring a window to the foreground by partial title match.
    
    Args:
        name: Partial window title to search for.
    
    Returns:
        Status message string.
    """
    if not HAS_WIN32:
        return "Window switching requires pywin32 to be installed."

    name_lower = name.lower()
    found_hwnd = None

    def enum_callback(hwnd, _):
        nonlocal found_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).lower()
            if name_lower in title:
                found_hwnd = hwnd

    win32gui.EnumWindows(enum_callback, None)

    if found_hwnd:
        win32gui.ShowWindow(found_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(found_hwnd)
        logger.info(f"Switched to window matching: {name!r}")
        return f"Switched to {name}."
    else:
        return f"No open window found matching '{name}'."


def list_running_apps() -> str:
    """Return a summary of notable running applications."""
    notable = []
    seen = set()

    for proc in psutil.process_iter(["name"]):
        try:
            pname = proc.info["name"]
            if pname and pname not in seen:
                seen.add(pname)
                # Filter to user-facing apps only
                for alias, exe in APP_ALIASES.items():
                    if exe.lower() == pname.lower():
                        notable.append(alias.title())
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if notable:
        return "Currently running: " + ", ".join(sorted(set(notable))) + "."
    else:
        return "No notable applications detected running."
