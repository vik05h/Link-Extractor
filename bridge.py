"""RPC bridge between the WebView2 frontend and the Python modules.

This is an adapter only: it translates calls from window.pywebview.api into module
calls and sends events back. Decisions live in the modules behind it. Internal
references stay private, because pywebview reflects public attributes into JavaScript.
"""

import json
import logging
import os
import re
import sqlite3
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import pyperclip

import community
import engine
import game_records
import integrations
import issues
import links
import palette
import scraper
import telemetry
import updater
import utils
import validator
from history import HistoryManager
from pipeline import ExtractionPipeline, PipelinePorts

log = logging.getLogger(__name__)

SAVABLE_SETTINGS = {
    "concurrency",
    "auto_validate",
    "jd_port",
    "community_auto_upload",
    "clipboard_sentinel_enabled",
    "auto_crash_reporting",
}
CLIPBOARD_POLL_SECONDS = 1.5
RESOLVABLE_CLIPBOARD_TYPES = {"fitgirl_game_page", "fitgirl_pastebin", "fuckingfast_direct", "raw_links"}
DUPLICATE_CHOICE_TIMEOUT_SECONDS = 60.0


class AppBridge:
    def __init__(self):
        self._window = None
        self._settings = utils.load_settings()
        self._history = HistoryManager()
        self._cancel_event = threading.Event()
        self._is_running = False
        self._run_lock = threading.Lock()
        self._clipboard_running = False
        self._last_clipboard_val = ""
        self._duplicate_wait_event = threading.Event()
        self._duplicate_action: Optional[str] = None
        self._instance_id = f"proc_{os.getpid()}_{int(time.time()) % 10000}"
        self._update_available = False
        self._latest_release_info: Optional[Dict[str, Any]] = None
        self._update_downloading = False
        self._update_cancel_event = threading.Event()
        self._verified_update_path: Optional[str] = None

    def bind_window(self, window):
        """Attach the pywebview window and start the background watchers."""
        self._window = window
        self._start_clipboard_sentinel()
        threading.Thread(target=self._check_updates_at_startup, daemon=True, name="update-check").start()

    def dispatch_event(self, event_name: str, payload: Any = None):
        """Send a CustomEvent to the frontend."""
        if not self._window:
            return
        data = json.dumps(payload if payload is not None else {})
        try:
            self._window.evaluate_js(f"window.dispatchEvent(new CustomEvent('{event_name}', {{ detail: {data} }}));")
        except Exception:
            log.exception("Could not send event %s", event_name)

    # ==========================================
    # Clipboard Sentinel
    # ==========================================

    def _start_clipboard_sentinel(self) -> None:
        if self._clipboard_running:
            return
        self._clipboard_running = True

        def watch() -> None:
            while self._clipboard_running:
                if self._settings.get("clipboard_sentinel_enabled", True):
                    try:
                        self._check_clipboard((pyperclip.paste() or "").strip())
                    except pyperclip.PyperclipException as error:
                        log.debug("Clipboard unavailable: %s", error)
                time.sleep(CLIPBOARD_POLL_SECONDS)

        threading.Thread(target=watch, daemon=True, name="clipboard-sentinel").start()

    def _check_clipboard(self, value: str) -> None:
        if not value or value == self._last_clipboard_val:
            return
        self._last_clipboard_val = value
        url_type = scraper.detect_url_type(value)
        if url_type in RESOLVABLE_CLIPBOARD_TYPES:
            slug = game_records.generate_game_slug(value) if url_type == "fitgirl_game_page" else ""
            self.dispatch_event("clipboard:detected", {"url": value, "url_type": url_type, "slug": slug})

    def copy_to_clipboard(self, text: str) -> Dict[str, Any]:
        """Copy text for the user. The sentinel is told so it does not react to the app's own copy."""
        clean = text or ""
        self._last_clipboard_val = clean.strip()
        try:
            pyperclip.copy(clean)
            return {"success": True}
        except pyperclip.PyperclipException as error:
            return {"success": False, "error": str(error)}

    # ==========================================
    # URL & Game Lookup
    # ==========================================

    def detect_url(self, url: str) -> Dict[str, Any]:
        clean_url = (url or "").strip()
        url_type = scraper.detect_url_type(clean_url)
        slug = game_records.generate_game_slug(clean_url) if url_type == "fitgirl_game_page" else ""
        return {"url": clean_url, "url_type": url_type, "slug": slug}

    def check_existing_game(self, url_or_slug: str) -> Dict[str, Any]:
        """Look for exactly this game in the community cache and local history."""
        try:
            history = self._history.get_records(limit=200)
        except sqlite3.Error:
            log.exception("Could not read history")
            history = []
        return community.find_existing_game(url_or_slug, history)

    def decide_duplicate(self, action: str) -> Dict[str, Any]:
        """The user's answer to the duplicate dialog: instant, fresh or cancel."""
        self._duplicate_action = action
        self._duplicate_wait_event.set()
        return {"status": "ok", "action": action}

    # ==========================================
    # Community Cloud Cache
    # ==========================================

    def _on_feed_synced(self, games: List[Dict[str, Any]]) -> None:
        self.dispatch_event("community:feed_updated", {"count": len(games), **community.feed_status()})

    def get_community_feed(self, force_refresh: bool = False) -> Dict[str, Any]:
        """The games known right now. If a refresh runs, community:feed_updated fires when it ends."""
        games = community.get_community_games(bool(force_refresh), on_synced=self._on_feed_synced)
        return {"games": games, **community.feed_status()}

    def get_game_urls(self, slug: str) -> List[str]:
        return community.get_game_urls(slug)

    def check_health(self, url: str) -> Dict[str, Any]:
        """A 1-byte check of a shared direct link. Other addresses are refused."""
        if not links.is_direct_link(url):
            return {"is_alive": False, "status_code": 0, "message": "Unsupported link"}
        link = validator.validate_single_url(0, url, timeout=6.0)
        message = link.content_length_str if link.is_valid else (link.error or "Link unreachable")
        return {"is_alive": link.is_valid, "status_code": link.status_code, "message": message}

    def ping_presence(self, session_id: str = "") -> Dict[str, Any]:
        """Renew the heartbeat in the background and return the last known count."""

        def ping() -> None:
            count = community.ping_presence((session_id or "").strip() or self._instance_id)
            self.dispatch_event("community:stats_updated", {"live_gamers": count})

        threading.Thread(target=ping, daemon=True, name="presence").start()
        return {"live_gamers": community.get_community_stats()["live_gamers"]}

    def track_game_usage(self, slug: str) -> Dict[str, Any]:
        return {"slug": slug, "used_count": community.increment_game_usage(slug)}

    def get_community_stats(self) -> Dict[str, Any]:
        return community.get_community_stats()

    def extract_game_palette(self, image_url: str) -> Dict[str, Any]:
        return palette.extract_game_palette(image_url)

    # ==========================================
    # Extraction Pipeline
    # ==========================================

    def start_extraction(self, url: str, concurrency: Optional[int] = None, force_fresh: bool = False) -> Dict[str, Any]:
        target = (url or "").strip()
        if not target:
            return {"status": "error", "message": "Empty URL provided."}
        with self._run_lock:
            if self._is_running:
                return {"status": "error", "message": "An extraction is already in progress."}
            self._is_running = True

        self._cancel_event.clear()
        self._duplicate_wait_event.clear()
        self._duplicate_action = None
        tabs = concurrency or self._settings.get("concurrency", 3)
        threading.Thread(
            target=self._run_pipeline, args=(target, tabs, bool(force_fresh)), daemon=True, name="extraction"
        ).start()
        return {"status": "started", "target_url": target}

    def _run_pipeline(self, target: str, concurrency: int, force_fresh: bool) -> None:
        ports = PipelinePorts(
            make_engine=lambda tabs: engine.ResolutionEngine(concurrency=tabs, headless=False),
            validate_links=validator.validate_links,
            fetch_game_page=scraper.extract_game_page_pastebins,
            resolve_paste_metadata=scraper.resolve_pastebin_metadata,
            publish=community.upload_game_record,
            find_existing=self.check_existing_game,
            ask_duplicate=self._ask_duplicate,
        )
        try:
            ExtractionPipeline(ports, self._history, self._settings, self.dispatch_event).run(
                target, concurrency, force_fresh, self._cancel_event
            )
        finally:
            self._is_running = False

    def _ask_duplicate(self, record: Dict[str, Any]) -> Optional[str]:
        self._duplicate_wait_event.clear()
        self.dispatch_event("pipeline:duplicate_detected", record)
        self._duplicate_wait_event.wait(timeout=DUPLICATE_CHOICE_TIMEOUT_SECONDS)
        return self._duplicate_action

    def cancel_pipeline(self) -> Dict[str, Any]:
        if not self._is_running:
            return {"status": "idle"}
        self._cancel_event.set()
        self._duplicate_wait_event.set()
        self.dispatch_event("pipeline:status", {"status": "cancelling", "message": "Cancelling workers..."})
        return {"status": "cancelling"}

    # ==========================================
    # JDownloader 2 & Export
    # ==========================================

    def push_to_jd2(self, urls: List[str], title: str, source_url: str = "") -> Dict[str, Any]:
        success, message = integrations.push_to_jdownloader(
            urls, package_name=title or "FitGirl Repack", source_url=source_url, port=self._settings.get("jd_port", 9666)
        )
        return {"success": success, "message": message}

    def export_urls(self, format_type: str, urls: List[str], title: str, total_size_str: str = "") -> Dict[str, Any]:
        """Export links to the Downloads folder as .txt, .json or .crawljob."""
        if not urls:
            return {"success": False, "message": "No URLs to export."}

        safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title or "repack").strip("_") or "repack"
        out_dir = utils.get_export_dir()
        os.makedirs(out_dir, exist_ok=True)

        if format_type == "txt":
            path = os.path.join(out_dir, f"{safe_title}_direct_urls.txt")
            written = integrations.export_text(path, urls, title)
        elif format_type == "json":
            path = os.path.join(out_dir, f"{safe_title}.json")
            written = integrations.export_json(path, title, "", urls, total_size_str)
        elif format_type == "crawljob":
            path = os.path.join(out_dir, f"{safe_title}.crawljob")
            written = integrations.export_crawljob(path, urls, title)
        else:
            return {"success": False, "message": f"Unsupported format: {format_type}"}

        if not written:
            return {"success": False, "message": f"Could not write {os.path.basename(path)}."}
        utils.open_folder_cross_platform(out_dir)
        return {"success": True, "file_path": path, "message": f"Saved {os.path.basename(path)} to Downloads!"}

    # ==========================================
    # History
    # ==========================================

    def get_history(self) -> List[Dict[str, Any]]:
        try:
            records = self._history.get_records()
        except sqlite3.Error:
            log.exception("Could not read history")
            return []
        return [
            {
                "id": record["id"],
                "game_title": record["title"],
                "source_url": record.get("source_url", ""),
                "parts_count": record.get("total_parts", 0),
                "resolved_count": record.get("resolved_count", 0),
                "is_partial": record.get("resolved_count", 0) < record.get("total_parts", 0),
                "total_size": record.get("total_size_str", "0 B"),
                "created_at": record.get("timestamp", "Recently"),
                "resolved_links": record.get("urls", []),
            }
            for record in records
        ]

    def delete_history_item(self, record_id: int) -> Dict[str, Any]:
        try:
            self._history.delete_record(int(record_id))
            return {"success": True}
        except (sqlite3.Error, TypeError, ValueError) as error:
            return {"success": False, "error": str(error)}

    # ==========================================
    # Settings
    # ==========================================

    def get_settings(self) -> Dict[str, Any]:
        self._settings = utils.load_settings()
        return self._settings

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Save the options the Settings screen offers, and nothing else."""
        self._settings.update({key: value for key, value in new_settings.items() if key in SAVABLE_SETTINGS})
        utils.save_settings(self._settings)
        return {"success": True}

    # ==========================================
    # Updater
    # ==========================================

    def _check_updates_at_startup(self) -> None:
        time.sleep(3.5)
        has_update, release_info, message = updater.check_for_updates()
        log.info("Startup update check: %s", message)
        if has_update and release_info:
            self._update_available = True
            self._latest_release_info = release_info
            self.dispatch_event("updater:available", {
                "release_info": release_info,
                "is_frozen": updater.is_running_frozen(),
                "current_version": updater.CURRENT_VERSION,
            })

    def get_changelogs(self) -> List[Dict[str, Any]]:
        return updater.get_all_version_changelogs()

    def get_update_status(self) -> Dict[str, Any]:
        return {
            "has_update": self._update_available,
            "release_info": self._latest_release_info,
            "current_version": updater.CURRENT_VERSION,
            "is_frozen": updater.is_running_frozen(),
        }

    def check_for_updates(self) -> Dict[str, Any]:
        has_update, release_info, message = updater.check_for_updates()
        self._update_available = has_update
        self._latest_release_info = release_info if has_update else None
        return {
            "has_update": has_update,
            "available": has_update,
            "release_info": release_info or {},
            "message": message,
            "is_frozen": updater.is_running_frozen(),
            "current_version": updater.CURRENT_VERSION,
        }

    def start_update_download(self) -> Dict[str, Any]:
        """Download the update found by the last check. The page cannot choose what gets downloaded."""
        if self._update_downloading:
            return {"status": "downloading", "message": "Download already in progress."}

        release_info = self._latest_release_info
        if not release_info:
            _, release_info, _ = updater.check_for_updates()
        if not release_info or not release_info.get("has_binary"):
            return {"status": "error", "message": "This release has no installer attached."}

        self._update_cancel_event = threading.Event()
        self._update_downloading = True
        self._verified_update_path = None
        threading.Thread(target=self._download_update, args=(release_info,), daemon=True, name="update-download").start()
        return {"status": "started"}

    def _download_update(self, release_info: Dict[str, Any]) -> None:
        def progress(downloaded: int, total: int, percent: float, speed: float) -> None:
            self.dispatch_event("updater:progress", {
                "downloaded": downloaded,
                "total": total,
                "percent": round(percent, 1),
                "speed_str": f"{speed / 1048576:.1f} MB/s" if speed > 0 else "Calculating...",
                "downloaded_str": f"{downloaded / 1048576:.1f} MB",
                "total_str": f"{total / 1048576:.1f} MB" if total > 0 else "Unknown",
            })

        try:
            path = updater.download_update(release_info, progress, self._update_cancel_event)
        except updater.UpdateCancelled:
            self.dispatch_event("updater:download_cancelled", {})
        except updater.UpdateError as error:
            log.warning("Update rejected: %s", error)
            self.dispatch_event("updater:error", {"error": str(error)})
        else:
            self._verified_update_path = path
            size = os.path.getsize(path)
            self.dispatch_event("updater:download_complete", {
                "file_path": path,
                "is_frozen": updater.is_running_frozen(),
                "file_size": size,
                "file_size_str": f"{size / 1048576:.1f} MB",
            })
        finally:
            self._update_downloading = False

    def cancel_update_download(self) -> Dict[str, Any]:
        self._update_cancel_event.set()
        return {"status": "cancelled"}

    def apply_update_and_restart(self) -> Dict[str, Any]:
        """Install the file verified in this session, and never a leftover from an earlier run."""
        path = self._verified_update_path
        if not path or not os.path.exists(path):
            return {"status": "error", "message": "No verified update has been downloaded."}
        if not updater.apply_update_and_restart(path):
            return {"status": "not_frozen", "message": "Application is running in Python dev mode."}
        threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0)), daemon=True).start()
        return {"status": "restarting"}

    def launch_downloaded_binary(self) -> Dict[str, Any]:
        path = self._verified_update_path
        if not path or not os.path.exists(path):
            return {"status": "not_found", "message": "No verified update has been downloaded."}
        return {"status": "launched" if updater.launch_downloaded_executable(path) else "error"}

    def open_updates_folder(self) -> Dict[str, Any]:
        return {"status": "opened", "path": updater.open_updates_folder()}

    # ==========================================
    # Community Issue Center
    # ==========================================

    def get_all_reports(self) -> Dict[str, Any]:
        reached, reports, message = issues.fetch_all_reports()
        return {"success": reached, "reports": reports, "message": message}

    def submit_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a report. Returns success with queued=True if it is saved but not delivered yet."""
        result = issues.submit_user_report(
            subject=data.get("subject", ""),
            category=data.get("category", "Bug Report"),
            description=data.get("description", ""),
            screenshot_data=data.get("screenshot_data", ""),
            telemetry={
                "app_version": updater.CURRENT_VERSION,
                "platform": sys.platform,
                "theme": self._settings.get("theme", ""),
            },
            force_create=bool(data.get("force_create", False)),
        )
        return {
            "success": result.outcome in ("sent", "queued"),
            "queued": result.outcome == "queued",
            "is_duplicate": result.outcome == "duplicate",
            "report_id": result.report_id,
            "record": result.record,
            "message": result.message,
        }

    def upvote_report(self, report_id: str) -> Dict[str, Any]:
        success, count = issues.increment_report_affected(str(report_id))
        return {"success": success, "new_count": count}

    def get_report_screenshot(self, report_id: str, key: str = issues.REPORT_SCREENSHOT_KEY) -> Dict[str, Any]:
        data = issues.get_screenshot(str(report_id), str(key))
        return {"success": bool(data), "screenshot_data": data}

    def verify_admin_key(self, candidate_key: str) -> Dict[str, Any]:
        """Ask the database whether this key has admin rights."""
        valid, message = issues.verify_admin_key(str(candidate_key))
        return {"success": valid, "message": message}

    def admin_update_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        success, message = issues.update_report(
            data.get("report_id", ""), data.get("status", "open"), data.get("admin_remark", ""), data.get("admin_key", "")
        )
        return {"success": success, "message": message}

    def admin_delete_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        success, message = issues.delete_report(data.get("report_id", ""), data.get("admin_key", ""))
        return {"success": success, "message": message}

    def add_report_comment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        success, result, comment = issues.add_comment(
            report_id=data.get("report_id", ""),
            text=data.get("text", ""),
            author_type=data.get("author_type", "gamer"),
            author_name=data.get("author_name", ""),
            screenshot_data=data.get("screenshot_data", ""),
            admin_key=data.get("admin_key", ""),
        )
        return {
            "success": success,
            "comment_id": result if success else "",
            "comment": comment,
            "message": "Comment posted successfully!" if success else result,
        }

    def delete_report_comment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        success, message = issues.delete_comment(
            data.get("report_id", ""), data.get("comment_id", ""), data.get("admin_key", "")
        )
        return {"success": success, "message": message}

    def report_client_crash(self, message: Any, stack_trace: str = "") -> Dict[str, Any]:
        """Forward a frontend error to crash reporting, which applies the opt-out and cleaning."""
        success, crash_id = telemetry.report_crash_log(
            "ClientError", str(message), str(stack_trace), context="frontend_runtime", extra={"client": "WebView2_Svelte"}
        )
        return {"success": success, "crash_id": crash_id}
