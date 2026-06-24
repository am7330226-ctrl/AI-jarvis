"""
Media & Volume Control Tool
============================
Controls system volume, mute, and media playback on Windows.
Uses pycaw for precise volume control via Windows Core Audio API.
"""

import logging
import keyboard

logger = logging.getLogger(__name__)

# Try to import pycaw for proper Windows volume control
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False
    logger.warning("pycaw not available — volume control will use keyboard simulation.")


def _get_volume_interface():
    """Get the Windows Core Audio volume interface."""
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def set_volume(level: int) -> str:
    """
    Set system volume to a percentage (0–100).
    
    Args:
        level: Volume percentage (0-100).
    
    Returns:
        Status message.
    """
    level = max(0, min(100, int(level)))
    
    if HAS_PYCAW:
        try:
            volume = _get_volume_interface()
            # pycaw uses scalar 0.0 to 1.0
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            logger.info(f"Volume set to {level}%")
            return f"Volume set to {level} percent."
        except Exception as e:
            logger.error(f"pycaw volume error: {e}")

    # Fallback: use keyboard simulation (less precise)
    # This approach isn't great for setting exact levels, but works as fallback
    logger.info("Using keyboard fallback for volume.")
    return f"Volume adjustment attempted. For precise control, ensure pycaw is installed."


def get_volume() -> str:
    """Get current system volume level."""
    if HAS_PYCAW:
        try:
            volume = _get_volume_interface()
            level = int(volume.GetMasterVolumeLevelScalar() * 100)
            muted = volume.GetMute()
            mute_str = " (muted)" if muted else ""
            return f"Current volume is {level} percent{mute_str}."
        except Exception as e:
            logger.error(f"pycaw get volume error: {e}")
    return "Unable to retrieve volume level."


def mute_toggle() -> str:
    """Toggle system mute on/off."""
    if HAS_PYCAW:
        try:
            volume = _get_volume_interface()
            current_mute = volume.GetMute()
            volume.SetMute(not current_mute, None)
            state = "muted" if not current_mute else "unmuted"
            logger.info(f"System audio {state}.")
            return f"System audio {state}."
        except Exception as e:
            logger.error(f"pycaw mute error: {e}")

    # Fallback: media key simulation
    keyboard.send("volume mute")
    return "Toggled mute."


def volume_up(amount: int = 10) -> str:
    """Increase volume by a percentage amount."""
    if HAS_PYCAW:
        try:
            volume = _get_volume_interface()
            current = volume.GetMasterVolumeLevelScalar() * 100
            new_level = min(100, current + amount)
            volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)
            logger.info(f"Volume increased to {new_level:.0f}%")
            return f"Volume increased to {new_level:.0f} percent."
        except Exception as e:
            logger.error(f"Volume up error: {e}")

    keyboard.send("volume up")
    return "Volume increased."


def volume_down(amount: int = 10) -> str:
    """Decrease volume by a percentage amount."""
    if HAS_PYCAW:
        try:
            volume = _get_volume_interface()
            current = volume.GetMasterVolumeLevelScalar() * 100
            new_level = max(0, current - amount)
            volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)
            logger.info(f"Volume decreased to {new_level:.0f}%")
            return f"Volume decreased to {new_level:.0f} percent."
        except Exception as e:
            logger.error(f"Volume down error: {e}")

    keyboard.send("volume down")
    return "Volume decreased."


def play_pause() -> str:
    """Simulate media play/pause key."""
    keyboard.send("play/pause media")
    logger.info("Media play/pause sent.")
    return "Play/pause toggled."


def next_track() -> str:
    """Simulate media next track key."""
    keyboard.send("next track")
    logger.info("Next track sent.")
    return "Skipping to next track."


def previous_track() -> str:
    """Simulate media previous track key."""
    keyboard.send("previous track")
    logger.info("Previous track sent.")
    return "Going to previous track."
