import os
import sys
import json
import time
import subprocess
import threading
import urllib.request
import urllib.parse
import webbrowser
from typing import Optional, Dict, Any, Tuple, Callable, List

import utils

CURRENT_VERSION = "v3.2.0"
GITHUB_REPO = "vik05h/Link-Extractor"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
FALLBACK_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"

VERSION_CHANGELOGS: Dict[str, Dict[str, Any]] = {
    "v3.2.0": {
        "title": "Community Cloud Cache, Pixel Dino Loader & 3D Repack Hub",
        "highlights": [
            "Decentralized Community Cloud Cache powered by Firebase Realtime Database lightweight REST API.",
            "Retro 8-bit Arcade Pixel Dino running loading animation with live cloud status updates.",
            "Interactive 3D-styled Game Cards with cover thumbnails, depth glow, and local timezone intelligence.",
            "Automatic instant pre-fetched link detection on Extractor screen with 1-click skip browser option.",
            "1-Click Health Check executing rapid 1-byte verification on Part 1 of any community repack.",
            "Automated background cloud publishing with privacy opt-out toggle in Settings & Tweaks.",
            "Freshness color badges (⚡ Fresh <12h, ⏳ Aging 12-36h, ⚠️ Expired >36h) with local time display."
        ],
        "bug_fixes": [
            "Enforced strict overwrite logic to ensure newest extraction timestamps update cloud records.",
            "Added graceful offline fallback with built-in community cache when Firebase is unreachable.",
            "Added full entity unescaping and cover image extraction for FitGirl game pages."
        ]
    },
    "v3.1.1": {
        "title": "Startup Auto-Updater, Real-Time Async UI & In-App Installer",
        "highlights": [
            "Automatic silent update check on application startup with user confirmation prompt.",
            "In-app background download progress dialog displaying live speed and percentage.",
            "Automated Windows binary replacement and seamless application restart launcher.",
            "Interactive What's New & Bug Fixes release notes popup dialog on updated version launch.",
            "Off-screen headed Playwright browser engine preventing OS window focus theft."
        ],
        "bug_fixes": [
            "Fixed real-time UI freezing by transitioning to Flet's native async event loop.",
            "Fixed DataTable child mutation rendering using state model rebuild pattern.",
            "Fixed SegmentedButton JSON serialization error with set-to-list conversion.",
            "Improved detached updater batch script cleanup and process PID tracking on Windows."
        ]
    },
    "v3.1.0": {
        "title": "Material 3 Engine, 1-Byte Size Validation & SQLite History Archive",
        "highlights": [
            "Full Material 3 UI migration with Flutter hardware acceleration (60-120 FPS).",
            "Rapid concurrent 1-byte HTTP Range size validation and live total repack calculation.",
            "Integrated local SQLite download archive with instant search and 1-click re-export.",
            "JDownloader 2 FlashGot HTTP API push with #filename.rar zero-prompt anchors.",
            "Dynamic Material 3 theme seeds, branding logo switcher, and transition presets.",
            "Automatic startup update checker and automated in-app update installer."
        ],
        "bug_fixes": [
            "Fixed PyInstaller icons.json missing resource crash on standalone Windows binary.",
            "Fixed window and taskbar icon binding to eliminate Flutter runner default icon.",
            "Fixed Flet AnimatedSwitcher hot-swapping duration freeze.",
            "Fixed cross-platform export directory path resolution on non-standard Windows drives.",
            "Fixed race conditions during mid-extraction cancellations."
        ]
    },
    "v3.0.0": {
        "title": "High-Speed Playwright Multi-Tab Engine & Turnstile Solver",
        "highlights": [
            "Parallel multi-tab browser pool resolving parts concurrently (3x-6x speedup).",
            "Automatic Cloudflare Turnstile captcha solver and response header interceptor.",
            "Automated retry engine with jitter delays for dropped links.",
            "Direct FitGirl game page and pastebin auto-detection."
        ],
        "bug_fixes": [
            "Resolved browser memory leak by sharing a single context across worker tabs.",
            "Fixed link parser edge cases on multi-mirror pastebins."
        ]
    }
}


def parse_version(v_str: str) -> tuple:
    """Parse version string like 'v3.1.0' or '3.1' into comparable tuple (3, 1, 0)."""
    clean = v_str.strip().lstrip("vV")
    parts = []
    for p in clean.split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def check_for_updates(current_version: str = CURRENT_VERSION, timeout: float = 5.0) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Check GitHub Releases for newer version of the application.
    Returns:
      (has_update: bool, release_info: Optional[dict], message: str)
    """
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": f"FitGirlLinkExtractor/{current_version}",
            "Accept": "application/vnd.github.v3+json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                latest_tag = data.get("tag_name", "")
                release_name = data.get("name", latest_tag)
                release_body = data.get("body", "No changelog provided.")
                html_url = data.get("html_url", FALLBACK_RELEASES_URL)

                # Check downloadable binary assets
                assets = data.get("assets", [])
                download_url = html_url
                asset_size = 0
                for a in assets:
                    if a.get("name", "").endswith(".exe"):
                        download_url = a.get("browser_download_url", html_url)
                        asset_size = a.get("size", 0)
                        break

                curr_tuple = parse_version(current_version)
                latest_tuple = parse_version(latest_tag)

                release_info = {
                    "current_version": current_version,
                    "latest_version": latest_tag,
                    "name": release_name,
                    "body": release_body,
                    "html_url": html_url,
                    "download_url": download_url,
                    "asset_size": asset_size,
                    "published_at": data.get("published_at", "")
                }

                if latest_tuple > curr_tuple:
                    return True, release_info, f"New version {latest_tag} is available!"
                else:
                    return False, release_info, f"You are running the latest version ({current_version})."

            return False, None, f"GitHub returned status {resp.status}."

    except urllib.error.HTTPError as he:
        if he.code == 404:
            return False, None, "No releases published yet on GitHub."
        return False, None, f"HTTP Error {he.code}: Could not check for updates."
    except Exception as e:
        return False, None, f"Update check failed: {e}"


def get_version_changelog(version: str) -> Dict[str, Any]:
    """Retrieve structured changelog for given version with offline fallback."""
    clean_v = version if version.startswith("v") else f"v{version}"
    if clean_v in VERSION_CHANGELOGS:
        data = VERSION_CHANGELOGS[clean_v].copy()
        data["version"] = clean_v
        return data

    # Fallback default
    return {
        "version": clean_v,
        "title": f"FitGirl Link Extractor {clean_v}",
        "highlights": [
            "Performance and stability enhancements.",
            "Updated direct link extraction algorithms.",
            "Refined user interface and workflow responsiveness."
        ],
        "bug_fixes": [
            "General bug fixes and security improvements."
        ]
    }


def download_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> str:
    """
    Download update binary from URL to app data updates directory.
    Returns path to downloaded file.
    """
    updates_dir = os.path.join(utils.get_app_data_dir(), "updates")
    os.makedirs(updates_dir, exist_ok=True)
    target_path = os.path.join(updates_dir, "LinkExtractor_update.exe")

    if os.path.exists(target_path):
        try:
            os.remove(target_path)
        except Exception:
            pass

    req = urllib.request.Request(
        download_url,
        headers={
            "User-Agent": f"FitGirlLinkExtractor/{CURRENT_VERSION}",
            "Accept": "application/octet-stream"
        }
    )

    with urllib.request.urlopen(req, timeout=30.0) as resp:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 64 * 1024  # 64 KB

        with open(target_path, "wb") as out_file:
            while True:
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("Download cancelled by user.")
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    pct = (downloaded / total_size * 100.0) if total_size > 0 else 0.0
                    progress_callback(downloaded, total_size, pct)

    return target_path


def apply_update_and_restart(downloaded_file_path: str) -> bool:
    """
    Spawn detached updater script to replace running binary and relaunch application.
    Works for frozen Windows executables; for dev mode, notifies the user.
    """
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        dest_exe = sys.executable
        current_pid = os.getpid()
        updates_dir = os.path.dirname(downloaded_file_path)
        bat_path = os.path.join(updates_dir, "apply_update.bat")

        bat_content = f"""@echo off
chcp 65001 > nul
set PID={current_pid}
set "SRC={downloaded_file_path}"
set "DEST={dest_exe}"

:wait_loop
tasklist /fi "pid eq %PID%" 2>nul | find "%PID%" >nul
if %ERRORLEVEL% == 0 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

timeout /t 1 /nobreak >nul

copy /y "%SRC%" "%DEST%" >nul
if errorlevel 1 (
    move /y "%SRC%" "%DEST%" >nul
)

del "%SRC%" >nul 2>&1

start "" "%DEST%"

del "%~f0" >nul 2>&1
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            close_fds=True
        )
        return True

    return False


def open_release_page(url: Optional[str] = None):
    """Open release page or latest download URL in default web browser."""
    target = url or FALLBACK_RELEASES_URL
    webbrowser.open(target)
