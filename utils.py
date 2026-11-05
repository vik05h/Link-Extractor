import os
import sys
import json
import time
import threading
import subprocess
import logging
import logging.handlers
from typing import Dict, Any

log = logging.getLogger(__name__)


def get_app_data_dir() -> str:
    """Get persistent user data directory for settings and history database."""
    if getattr(sys, 'frozen', False):
        app_data = os.environ.get('APPDATA')
        if app_data:
            dir_path = os.path.join(app_data, 'FitGirlLinkExtractor')
            os.makedirs(dir_path, exist_ok=True)
            return dir_path
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to bundled resource (works in dev and PyInstaller single-file)."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path.replace("/", os.sep))


def get_export_dir() -> str:
    """Get user-friendly export directory (Downloads folder or app folder) dynamically across all OSes and drives."""
    # 1. Cross-platform home directory detection via os.path.expanduser('~')
    home_dir = os.path.expanduser("~")
    downloads = os.path.join(home_dir, "Downloads")
    if os.path.exists(downloads):
        return downloads

    # 2. Check Windows USERPROFILE environment variable if custom drive
    user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if user_profile:
        dl = os.path.join(user_profile, "Downloads")
        if os.path.exists(dl):
            return dl
        return user_profile

    # 3. Fallback to application directory
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def open_folder_cross_platform(folder_path: str):
    """Open folder in native file manager on Windows (Explorer), macOS (Finder), or Linux."""
    try:
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder_path], check=False)
        else:
            subprocess.run(["xdg-open", folder_path], check=False)
    except OSError as error:
        log.warning("Could not open folder %s: %s", folder_path, error)


def load_settings() -> Dict[str, Any]:
    """Load user settings from persistent JSON file with defaults."""
    settings: Dict[str, Any] = {
        "concurrency": 3,
        "auto_validate": True,
        "jd_port": 9666,
        "community_auto_upload": True,
        "clipboard_sentinel_enabled": True,
        "auto_crash_reporting": True,
    }
    settings_file = os.path.join(get_app_data_dir(), "settings.json")
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            settings.update(data)
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as error:
        log.warning("Ignoring unreadable settings file: %s", error)
    return settings


def setup_logging() -> None:
    """Log to a small rotating file in the app data folder, since a windowed exe has no console."""
    log_dir = os.path.join(get_app_data_dir(), "logs")
    handlers: list = []
    try:
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "app.log"), maxBytes=1024 * 1024, backupCount=3, encoding="utf-8"
        ))
    except OSError as error:
        print(f"File logging unavailable: {error}", file=sys.stderr)
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)


def write_json_atomic(path: str, data: Any) -> None:
    """Write JSON so a crash mid-write can never leave a half-written file behind."""
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)


def save_settings(settings: Dict[str, Any]):
    """Persist user settings to JSON file."""
    settings_file = os.path.join(get_app_data_dir(), "settings.json")
    try:
        write_json_atomic(settings_file, settings)
    except OSError:
        log.exception("Could not save settings")


def apply_windows_native_icon(ico_path="app_icon.ico"):
    """Bind the native window and taskbar icon on Windows."""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    abs_ico = os.path.join(base_dir, ico_path)
    if not os.path.exists(abs_ico):
        abs_ico = os.path.abspath(ico_path)
    if not os.path.exists(abs_ico):
        return

    WM_SETICON = 0x0080
    ICON_SMALL = 0
    ICON_BIG = 1
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040
    GCLP_HICON = -14
    GCLP_HICONSM = -34

    try:
        user32 = ctypes.windll.user32
        h_icon = user32.LoadImageW(None, abs_ico, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        if not h_icon:
            return

        def _apply_loop():
            for _ in range(35):
                time.sleep(0.5)
                found = []

                @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                def enum_cb(hwnd, lparam):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        if "link extractor" in buf.value.lower():
                            found.append(hwnd)  # noqa: B023 (called immediately by EnumWindows below)
                    return True

                user32.EnumWindows(enum_cb, 0)
                for hwnd in found:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon)
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon)
                    try:
                        if hasattr(user32, 'SetClassLongPtrW'):
                            user32.SetClassLongPtrW(hwnd, GCLP_HICON, h_icon)
                            user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, h_icon)
                        else:
                            user32.SetClassLongW(hwnd, GCLP_HICON, h_icon)
                            user32.SetClassLongW(hwnd, GCLP_HICONSM, h_icon)
                    except (OSError, ctypes.ArgumentError) as error:
                        log.debug("Could not set the window class icon: %s", error)
                if found:
                    time.sleep(1.0)
                    for hwnd in found:
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon)
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon)
                    break

        threading.Thread(target=_apply_loop, daemon=True).start()
    except (OSError, AttributeError, ctypes.ArgumentError) as error:
        log.info("Could not set the window icon: %s", error)
