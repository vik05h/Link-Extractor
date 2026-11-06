"""GitHub Releases update check and in-app installer.

An update replaces the running program, so a bad file would break the install.
A download is only accepted after its source, size, SHA-256 and file type all check
out, and the script that swaps the file keeps a backup and can put it back.
"""

import hashlib
import http.client
import logging
import os
import sys
import json
import time
import subprocess
import threading
import urllib.error
import urllib.request
from typing import Optional, Dict, Any, Tuple, Callable, List

import utils
from version import APP_VERSION

log = logging.getLogger(__name__)

CURRENT_VERSION = APP_VERSION
GITHUB_REPO = "vik05h/Link-Extractor"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
FALLBACK_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
RELEASE_DOWNLOAD_PREFIX = f"https://github.com/{GITHUB_REPO}/releases/download/"
UPDATE_FILE_NAME = "LinkExtractor_update.exe"
BACKUP_FILE_NAME = "LinkExtractor_previous.exe"


class UpdateError(Exception):
    """The update could not be downloaded or did not pass its checks."""


class UpdateCancelled(Exception):
    """The user cancelled the download."""

VERSION_CHANGELOGS: Dict[str, Dict[str, Any]] = {
    "v3.9.0": {
        "title": "Liquid Glass Interface, Glass Bubble Navigation, New Logo & Guided Tour Rework",
        "highlights": [
            "Liquid Glass surfaces with real refraction across the sidebar, top bars, game cards, Stage panels, dialogs and toasts, with a Settings switch for plain frosted glass and an automatic fallback on slower PCs.",
            "Glass bubble navigation on the sidebar and the Stage tab bar: it springs between items, can be dragged like the iOS tab bar while it magnifies what is under it, and follows the arrow keys.",
            "The Stage tab row stays pinned under the URL bar, so long part lists scroll beneath it with Push to JD2 always in reach.",
            "New Bolt Tray logo across the app, splash, window, taskbar and .exe icon. Inside the app it takes the active theme's colors.",
            "Glass startup splash that loads the community games and first covers with real progress, then morphs into the app.",
            "Seven-step guided tour on a sample game, with hands-on Stage and filter steps. New installs start with the tour; updates open What's New, and the ? button replays the tour anytime.",
            "GenZ wording by default in the tour, splash, pop-ups and empty screens, with a Classic Wording switch in Settings. Buttons, errors and update messages stay plain."
        ],
        "bug_fixes": [
            "Links are judged by exact hostname, and shared records with any off-host link or out-of-scope source are rejected.",
            "Updates install only after their source, size, SHA-256 and file type check out, and the swap keeps a backup that is restored on failure.",
            "Admin rights are judged by the database; a local file no longer grants anything, and clients no longer delete shared game records.",
            "Cancelled runs keep nothing, only complete verified runs are published, and Verified 100% appears only when it is true.",
            "Dead links are told apart from links that could not be checked, and games are matched exactly instead of by substring.",
            "The crash report opt-out now covers Python crashes, and reports no longer include user names or secrets.",
            "The Hub heartbeat no longer downloads the whole feed, and report screenshots load only when asked.",
            "Fixed multi-link paste, history overwrites, empty usage records, and the clipboard watcher reacting to the app's own copies."
        ]
    },
    "v3.8.1": {
        "title": "Community Discussion Threads, Release Update Auto-Popup & Cyber Concurrency Slider",
        "highlights": [
            "Interactive Community Discussion Thread drawer on Issue Center tickets with badge attribution (Official Admin, Original Reporter, Community Gamer).",
            "One-click Engine Telemetry Log dumping directly into discussion replies for rapid collaborative bug diagnosis.",
            "Full screenshot attachment pipeline supporting file dropzone, file picker, and clipboard Ctrl+V pasting with client-side canvas compression.",
            "Administrative comment moderation and ticket status management protected by secure passkey authorization.",
            "Automatic release update popup notification on startup with session-based dismissal suppression to prevent repetitive popups.",
            "Cyberpunk animated concurrency slider in Settings with glowing thumb halo and tactile stepped performance tiers (Eco, Balanced, Turbo)."
        ],
        "bug_fixes": [
            "Fixed terminal hanging and application freeze when clicking Telemetry & Terminal tab by virtualizing log stream updates.",
            "Resolved content.d.ts type generation issue by configuring glob paths in tsconfig.json.",
            "Fixed comment normalization and timestamp sorting across Firebase Realtime Database and local JSON cache.",
            "Enforced constant-time cryptographic verification for Admin passkey authentication in AppData."
        ]
    },
    "v3.8.0": {
        "title": "Next-Gen Gaming Hub UI/UX Overhaul, Live Guided Tour & Community Issue Center",
        "highlights": [
            "Complete architectural migration from legacy Flet UI in v3.5.0 to hardware-accelerated desktop web architecture powered by Astro, Svelte, and Windows native WebView2.",
            "Interactive Live In-App Guided Tour actively spotlighting the URL bar, Community Vault, Defrag Stage, and Quick Actions with step-by-step onboarding.",
            "Community Issue Center featuring public issue tracking, smart duplicate prevention with affected-user count incrementing, and passkey-protected Admin remarks.",
            "Automated Firebase Crash Log capture intercepting unhandled Python and JavaScript errors with in-memory deduplication.",
            "Living Canvas dynamic ambient backlighting with mathematical vibrancy boosting extracting dominant colors from game cover art.",
            "Interactive Defrag Mosaic visualizer for real-time multi-part status tracking replacing static data tables.",
            "In-app automatic updater with live download speed HUD, percentage tracking, and detached Windows restart script.",
            "Multi-tier authoritative game artwork cascade extracting high-resolution FitGirl covers with procedural neon SVG fallback.",
            "Automated Pastebin metadata resolution extracting game names from archive filenames with FitGirl site search.",
            "Live concurrent gamer presence pulse indicator powered by zero-cost lightweight Firebase REST heartbeats.",
            "Selective Repack Filter saving tens of gigabytes by filtering optional language and bonus packs.",
            "Background Clipboard Sentinel auto-detecting copied FitGirl links and Web Audio API synthesized gaming sound haptics."
        ],
        "bug_fixes": [
            "Completely eliminated legacy Flet runtime thread blocking, socket buffering, and window focus stealing.",
            "Fixed ambient mode text darkness by implementing mathematical vibrancy boosting in HLS color space.",
            "Fixed 0 B repack size aggregation by aligning validator progress callback signature.",
            "Fixed Steam store 404 artwork failure on recent releases with authoritative FitGirl page parser.",
            "Fixed duplicate cache freshness logic ensuring cached mirrors older than 24 hours trigger fresh extractions."
        ]
    },
    "v3.5.0": {
        "title": "Interactive Live In-App Guided Tour, Spotlight Highlighting & Rebranding (Legacy Flet UI)",
        "highlights": [
            "Interactive Live In-App Guided Tour actively navigating across Extractor, Community Hub, History Archive, and Settings in real-time.",
            "Dynamic Spotlight Box Highlighting with glowing theme borders and soft shadows illuminating the exact target cards on each step.",
            "Complete Rebranding to 'Link Extractor' across window titles, PE resource headers, and in-app components.",
            "Display Framerate Selector toggling between 60 FPS (Balanced) and 120 FPS (Ultra Fluid) in real-time.",
            "Community Hub View Switcher with responsive Poster Grid View and Compact Feed List.",
            "Interactive Game Details Modal popup displaying all split repack archive parts with individual copy links.",
            "Enhanced Card Hover animations with theme-colored glowing borders, elevation pop, and smooth poster zoom.",
            "Expanded 8 dynamic Material 3 theme presets (Deep Violet, Emerald, Cyber Sapphire, Amber Gold, Neon Rose, Synthwave, Matrix, Crimson).",
            "Enhanced 1-Click Health Check with clear Part 1 verification badge and detailed tooltip."
        ],
        "bug_fixes": [
            "Fixed Icon.__init__() missing positional argument in tour controller.",
            "Fixed typing import for Callable in ui/state.py.",
            "Fixed shadow smudge glitch on lighter themes using native Material 3 elevation.",
            "Fixed missing utils import on Community view toggle.",
            "Added automatic SQLite History archive deduplication and smart upsert updates.",
            "Enforced pure-white high-contrast text and icons on floating status notifications."
        ]
    },
    "v3.2.0": {
        "title": "Community Cloud Cache, Pixel Dino Loader & 3D Repack Hub",
        "highlights": [
            "Decentralized Community Cloud Cache powered by Firebase Realtime Database lightweight REST API.",
            "Retro 8-bit Arcade Pixel Dino running loading animation with live cloud status updates.",
            "Interactive 3D-styled Game Cards with cover thumbnails, depth glow, and local timezone intelligence.",
            "Automatic instant pre-fetched link detection on Extractor screen with 1-click skip browser option.",
            "1-Click Health Check executing rapid 1-byte verification on Part 1 of any community repack.",
            "Automated background cloud publishing with privacy opt-out toggle in Settings & Tweaks.",
            "Freshness color badges (Fresh <12h, Aging 12-36h, Expired >36h) with local time display."
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
    """Parse version string like 'v3.1.0', '3.1', or 'v4.0.0-beta1' into comparable tuple (3, 1, 0)."""
    clean = v_str.strip().lstrip("vV")
    clean = clean.split("-")[0].split("+")[0]
    parts = []
    for p in clean.split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _find_installer(assets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for asset in assets:
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if name.endswith(".exe") and url.startswith(RELEASE_DOWNLOAD_PREFIX):
            return asset
    return None


def check_for_updates(
    current_version: str = CURRENT_VERSION,
    timeout: float = 5.0,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Check GitHub Releases for a newer version.
    Returns (has_update, release_info, message).
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
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        if he.code == 404:
            return False, None, "No releases published yet on GitHub."
        return False, None, f"HTTP Error {he.code}: Could not check for updates."
    except (OSError, ValueError, http.client.HTTPException) as e:
        return False, None, f"Update check failed: {e}"

    latest_tag = data.get("tag_name", "")
    html_url = data.get("html_url", FALLBACK_RELEASES_URL)
    installer = _find_installer(data.get("assets", []))

    release_info = {
        "current_version": current_version,
        "latest_version": latest_tag,
        "tag_name": latest_tag,
        "name": data.get("name", latest_tag),
        "body": data.get("body", "No changelog provided."),
        "html_url": html_url,
        "download_url": installer.get("browser_download_url", "") if installer else "",
        "asset_size": installer.get("size", 0) if installer else 0,
        "asset_digest": installer.get("digest", "") if installer else "",
        "has_binary": installer is not None,
        "published_at": data.get("published_at", "")
    }

    if parse_version(latest_tag) > parse_version(current_version):
        return True, release_info, f"New version {latest_tag} is available!"
    return False, release_info, f"You are running the latest version ({current_version})."


def get_all_version_changelogs() -> List[Dict[str, Any]]:
    """
    Returns all version changelogs sorted in descending semver order.
    Each item includes:
      - version: str (e.g. 'v3.8.0')
      - title: str
      - highlights: List[str]
      - bug_fixes: List[str]
      - is_current: bool (True if matches CURRENT_VERSION)
      - previous_version: Optional[str] (e.g. 'v3.5.0')
    """
    sorted_versions = sorted(
        VERSION_CHANGELOGS.keys(),
        key=lambda v: parse_version(v),
        reverse=True
    )
    results = []
    for idx, ver in enumerate(sorted_versions):
        entry = VERSION_CHANGELOGS[ver].copy()
        entry["version"] = ver
        entry["is_current"] = (ver == CURRENT_VERSION)
        entry["highlights"] = entry.get("highlights", [])
        entry["bug_fixes"] = entry.get("bug_fixes", [])
        prev_ver = sorted_versions[idx + 1] if idx + 1 < len(sorted_versions) else None
        entry["previous_version"] = prev_ver
        results.append(entry)
    return results


def _expected_sha256(release_info: Dict[str, Any]) -> str:
    digest = str(release_info.get("asset_digest") or "")
    algorithm, _, value = digest.partition(":")
    if algorithm != "sha256" or len(value) != 64:
        raise UpdateError("This release has no checksum, so it cannot be installed safely. Please use the release page.")
    return value.lower()


def _stream_download(
    url: str,
    target_path: str,
    progress_callback: Optional[Callable[[int, int, float, float], None]],
    cancel_event: Optional[threading.Event],
) -> Tuple[int, int, str]:
    """Save a URL to a file. Returns (bytes received, bytes announced, sha256)."""
    req = urllib.request.Request(
        url, headers={"User-Agent": f"FitGirlLinkExtractor/{CURRENT_VERSION}", "Accept": "application/octet-stream"}
    )
    hasher = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=30.0) as resp, open(target_path, "wb") as out_file:
        announced = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        last_time, last_bytes, speed = time.time(), 0, 0.0
        while True:
            if cancel_event and cancel_event.is_set():
                raise UpdateCancelled()
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            out_file.write(chunk)
            hasher.update(chunk)
            downloaded += len(chunk)

            now = time.time()
            if now - last_time >= 0.25:
                speed = (downloaded - last_bytes) / (now - last_time)
                last_time, last_bytes = now, downloaded
            if progress_callback:
                percent = (downloaded / announced * 100.0) if announced > 0 else 0.0
                progress_callback(downloaded, announced, percent, speed)
    return downloaded, announced, hasher.hexdigest()


def download_update(
    release_info: Dict[str, Any],
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> str:
    """
    Download and verify the release installer. Returns the path of the verified file.
    Raises UpdateError or UpdateCancelled, and leaves any earlier good download in place.
    """
    url = str(release_info.get("download_url") or "")
    if not url.startswith(RELEASE_DOWNLOAD_PREFIX):
        raise UpdateError("This release has no installer attached. Please use the release page.")
    expected_digest = _expected_sha256(release_info)
    expected_size = int(release_info.get("asset_size") or 0)

    updates_dir = os.path.join(utils.get_app_data_dir(), "updates")
    os.makedirs(updates_dir, exist_ok=True)
    target_path = os.path.join(updates_dir, UPDATE_FILE_NAME)
    partial_path = f"{target_path}.part"

    try:
        received, announced, actual_digest = _stream_download(url, partial_path, progress_callback, cancel_event)
        if announced and received != announced:
            raise UpdateError(f"The download stopped early ({received} of {announced} bytes). Please try again.")
        if expected_size and received != expected_size:
            raise UpdateError("The downloaded file has the wrong size. Please try again.")
        if actual_digest != expected_digest:
            raise UpdateError("The downloaded file failed its checksum, so it was not installed.")
        with open(partial_path, "rb") as check:
            if check.read(2) != b"MZ":
                raise UpdateError("The downloaded file is not a Windows program, so it was not installed.")
        os.replace(partial_path, target_path)
    except (OSError, ValueError, http.client.HTTPException) as error:
        raise UpdateError(f"The download failed: {error}") from error
    finally:
        try:
            os.remove(partial_path)
        except FileNotFoundError:
            pass
        except OSError as error:
            log.warning("Could not remove the partial download: %s", error)
    return target_path


def is_running_frozen() -> bool:
    """Return True if running as a PyInstaller compiled binary."""
    return getattr(sys, "frozen", False)


def launch_downloaded_executable(downloaded_file_path: str) -> bool:
    """Launch the downloaded standalone executable in a separate process."""
    if os.path.exists(downloaded_file_path):
        subprocess.Popen(
            [downloaded_file_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0,
            close_fds=True
        )
        return True
    return False


def open_updates_folder() -> str:
    """Open the updates folder in Windows Explorer."""
    updates_dir = os.path.join(utils.get_app_data_dir(), "updates")
    os.makedirs(updates_dir, exist_ok=True)
    utils.open_folder_cross_platform(updates_dir)
    return updates_dir


def _batch_quote(path: str) -> str:
    return path.replace("%", "%%")


def build_update_script(source: str, destination: str, backup: str, pid: int) -> str:
    """The batch script that swaps the exe once this process has exited.

    It backs up the old exe, retries while Windows still holds the file, compares the
    result byte for byte, and restores the backup if anything went wrong. Either way
    it starts the program again. The reset variable makes a PyInstaller one-file exe
    start clean instead of looking for the temp folder of the process that just exited.
    """
    return f"""@echo off
chcp 65001 > nul
set "SRC={_batch_quote(source)}"
set "DEST={_batch_quote(destination)}"
set "BACKUP={_batch_quote(backup)}"
set "PYINSTALLER_RESET_ENVIRONMENT=1"
set /a WAITED=0
set /a COPY_TRIES=0

:wait_for_exit
tasklist /fi "pid eq {pid}" 2>nul | find "{pid}" >nul
if errorlevel 1 goto exited
set /a WAITED+=1
if %WAITED% GEQ 60 goto start_program
ping -n 2 127.0.0.1 >nul
goto wait_for_exit

:exited
ping -n 2 127.0.0.1 >nul
if not exist "%SRC%" goto start_program
copy /y "%DEST%" "%BACKUP%" >nul
if errorlevel 1 goto start_program

:copy_new
copy /y "%SRC%" "%DEST%" >nul
if not errorlevel 1 goto verify_copy
set /a COPY_TRIES+=1
if %COPY_TRIES% GEQ 5 goto restore
ping -n 3 127.0.0.1 >nul
goto copy_new

:verify_copy
fc /b "%SRC%" "%DEST%" >nul
if errorlevel 1 goto restore
del "%SRC%" >nul 2>&1
goto start_program

:restore
copy /y "%BACKUP%" "%DEST%" >nul

:start_program
start "" "%DEST%"
(goto) 2>nul & del "%~f0"
"""


def apply_update_and_restart(downloaded_file_path: str) -> bool:
    """Start the swap script for a verified download. Returns False when not running as an exe."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False

    updates_dir = os.path.dirname(downloaded_file_path)
    bat_path = os.path.join(updates_dir, "apply_update.bat")
    backup_path = os.path.join(updates_dir, BACKUP_FILE_NAME)
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(build_update_script(downloaded_file_path, sys.executable, backup_path, os.getpid()))

    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
        cwd=updates_dir,
    )
    return True
