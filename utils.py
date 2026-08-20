import os
import sys
import json
import time
import threading
import subprocess
from typing import Dict, Any


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
    except Exception:
        pass


def load_settings() -> Dict[str, Any]:
    """Load user settings from persistent JSON file with defaults."""
    default_settings = {
        "concurrency": 3,
        "auto_validate": True,
        "jd_port": 9666,
        "theme_seed": "Deep Violet",
        "theme_mode": "Dark",
        "logo_style": "Minimalist Cyber Link",
        "animation_style": "Fast Subtle Fade",
        "headless": False
    }
    settings_file = os.path.join(get_app_data_dir(), "settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings


def save_settings(settings: Dict[str, Any]):
    """Persist user settings to JSON file."""
    settings_file = os.path.join(get_app_data_dir(), "settings.json")
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def apply_windows_native_icon(ico_path="app_icon.ico"):
    """Bind native window and taskbar icon on Windows to avoid Flutter default icon."""
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
            for _ in range(12):
                time.sleep(0.3)
                found = []

                @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                def enum_cb(hwnd, lparam):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buf, length + 1)
                            if "fitgirl direct link extractor" in buf.value.lower():
                                found.append(hwnd)
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
                    except Exception:
                        pass
                if found:
                    break

        threading.Thread(target=_apply_loop, daemon=True).start()
    except Exception:
        pass
