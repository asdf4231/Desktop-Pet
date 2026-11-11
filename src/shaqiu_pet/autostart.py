"""Launch-at-login registration for Windows.

Only the current user's own ``Run`` key is touched, and every failure degrades to
"not enabled" so a locked-down machine can never stop the pet from starting.
"""

import logging
import sys
from pathlib import Path

from shaqiu_pet.settings import PROJECT_ROOT

LOGGER = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "shaqiu"


def is_supported() -> bool:
    return sys.platform == "win32"


def default_command() -> str:
    """The command Windows should run at login for this installation."""
    script = PROJECT_ROOT / "desktop_pet.py"
    if script.exists():
        interpreter = Path(sys.executable)
        windowless = interpreter.with_name("pythonw.exe")
        if windowless.exists():
            interpreter = windowless
        return f'"{interpreter}" "{script}"'
    return f'"{sys.executable}" -m shaqiu_pet'


def _open_run_key(write: bool):
    import winreg

    access = winreg.KEY_SET_VALUE if write else winreg.KEY_READ
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, access)


def is_enabled() -> bool:
    if not is_supported():
        return False
    try:
        import winreg

        with _open_run_key(write=False) as key:
            value, _kind = winreg.QueryValueEx(key, VALUE_NAME)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        LOGGER.exception("Unable to read the autostart registry value")
        return False


def set_enabled(enabled: bool, command: str | None = None) -> bool:
    """Add or remove the login entry; returns whether the requested state holds."""
    if not is_supported():
        return False
    try:
        import winreg

        if enabled:
            with _open_run_key(write=True) as key:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command or default_command())
        else:
            try:
                with _open_run_key(write=True) as key:
                    winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
        return is_enabled() == enabled
    except OSError:
        LOGGER.exception("Unable to update the autostart registry value")
        return False


__all__ = ["VALUE_NAME", "default_command", "is_enabled", "is_supported", "set_enabled"]
