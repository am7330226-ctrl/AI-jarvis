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
import shutil
import webbrowser

# Common installation paths for applications on Windows
COMMON_APP_SEARCH_PATHS: dict = {
    "chrome.exe": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ],
    "msedge.exe": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "firefox.exe": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
    "brave.exe": [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ],
    "code.exe": [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "spotify.exe": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
    ],
    "discord.exe": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"),
    ],
}


def _find_executable_path(executable: str) -> str | None:
    """Find absolute path to an executable using PATH or common install directories."""
    # Check if executable is directly in PATH
    path_in_env = shutil.which(executable)
    if path_in_env:
        return path_in_env

    # Check known common paths
    exe_lower = executable.lower()
    if exe_lower in COMMON_APP_SEARCH_PATHS:
        for candidate in COMMON_APP_SEARCH_PATHS[exe_lower]:
            clean_path = candidate.split(" --")[0]  # strip flags if present
            if os.path.exists(clean_path):
                return candidate

    return None


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

    # Stage 1: Check if explicit file/folder path or URI protocol
    if executable.startswith("ms-"):
        try:
            subprocess.Popen(["cmd", "/c", "start", "", executable], shell=False)
            return f"Opened {name}."
        except Exception as e:
            logger.error(f"Error opening URI protocol {executable!r}: {e}")

    # Stage 2: Try resolved absolute path if available
    resolved_path = _find_executable_path(executable)
    target_to_launch = resolved_path if resolved_path else executable

    # Stage 3: Attempt launching via os.startfile
    if hasattr(os, 'startfile'):
        try:
            os.startfile(target_to_launch)
            return f"Opened {name}."
        except FileNotFoundError:
            logger.debug(f"os.startfile failed for {target_to_launch!r}, trying shell start...")
        except PermissionError:
            logger.error(f"Permission denied when launching {target_to_launch!r}")
            return f"Permission denied while trying to open {name}. Try running Jarvis as Administrator."
        except Exception as e:
            logger.warning(f"os.startfile exception ({e}), falling back to cmd start...")

    # Stage 4: Attempt Windows shell command `cmd /c start ""`
    try:
        subprocess.Popen(f'start "" "{executable}"', shell=True)
        return f"Opened {name}."
    except PermissionError:
        return f"Permission denied while trying to open {name}. Try running Jarvis as Administrator."
    except Exception as e:
        logger.error(f"Shell start failed for {executable!r}: {e}")

    # Stage 5: Browser fallback for web browsers
    if name_lower in ["chrome", "google chrome", "browser", "firefox", "edge", "brave"]:
        try:
            webbrowser.open("https://www.google.com")
            return f"Opened browser for {name}."
        except Exception as e:
            logger.error(f"Webbrowser fallback failed: {e}")

    return f"I couldn't find '{name}'. If it's a custom app or file, please provide the full path."



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
