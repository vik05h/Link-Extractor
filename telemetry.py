"""Anonymous crash reports. Off when the user opts out, and stripped of personal paths.

Every crash goes through report_crash_log, so the opt-out and the cleaning apply to
Python crashes and frontend errors alike.
"""

import hashlib
import logging
import os
import re
import sys
import threading
import time
import traceback
from typing import Any, Dict, Optional, Tuple

import firebase_client
import game_records
import utils
from firebase_client import FirebaseError
from version import APP_VERSION

log = logging.getLogger(__name__)

CRASH_LOGS_PATH = "crash_logs"

_reported = set()
_reported_lock = threading.Lock()

_WINDOWS_PROFILE = re.compile(r"([A-Za-z]:[\\/]+Users[\\/]+)[^\\/\"'\r\n]+")
_UNIX_PROFILE = re.compile(r"(/(?:home|Users)/)[^/\"'\s]+")
_URL_SECRET = re.compile(r"([?&](?:auth|token|access_token|key)=)[^&\s\"']+", re.IGNORECASE)


def sanitize_text(text: str) -> str:
    """Remove user names from file paths and secrets from URLs."""
    cleaned = str(text)
    home = os.path.expanduser("~")
    if home and home != "~":
        cleaned = cleaned.replace(home, "<home>").replace(home.replace("\\", "/"), "<home>")
    cleaned = _WINDOWS_PROFILE.sub(r"\1<user>", cleaned)
    cleaned = _UNIX_PROFILE.sub(r"\1<user>", cleaned)
    return _URL_SECRET.sub(r"\1<hidden>", cleaned)


def _enabled() -> bool:
    return utils.load_settings().get("auto_crash_reporting", True) is not False


def report_crash_log(
    error_type: str,
    error_message: str,
    traceback_str: str,
    context: str = "runtime",
    extra: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Send one crash report in the background. Returns (accepted, crash id or reason)."""
    if not _enabled():
        return True, "opted_out"

    message = sanitize_text(error_message)
    trace = sanitize_text(traceback_str)
    signature = hashlib.sha256(f"{error_type}:{message[:200]}:{trace[:200]}".encode("utf-8", "ignore")).hexdigest()
    with _reported_lock:
        if signature in _reported:
            return True, "already_reported"
        _reported.add(signature)

    crash_id = f"crash_{int(time.time())}_{signature[:6]}"
    payload = {
        "error_type": str(error_type)[:100],
        "error_message": message[:500],
        "traceback": trace[:5000],
        "context": str(context)[:50],
        "app_version": APP_VERSION,
        "platform": sys.platform,
        "timestamp_utc": game_records.utc_now_iso(),
        "telemetry": extra or {},
    }

    def send() -> None:
        try:
            firebase_client.request(f"{CRASH_LOGS_PATH}/{crash_id}", "PUT", payload, timeout=5.0)
        except FirebaseError as error:
            log.info("Crash report not delivered: %s", error)

    threading.Thread(target=send, daemon=True, name="crash-report").start()
    return True, crash_id


def install_exception_hooks() -> None:
    """Log and report unhandled exceptions on the main thread and on worker threads."""

    def on_main_thread_crash(exc_type, exc_value, exc_traceback) -> None:
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        log.critical("Unhandled exception\n%s", text)
        report_crash_log(exc_type.__name__, str(exc_value), text, context="unhandled_main_thread")
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def on_worker_thread_crash(args) -> None:
        text = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        log.critical("Unhandled exception in a worker thread\n%s", text)
        name = getattr(args.thread, "name", "worker")
        report_crash_log(args.exc_type.__name__, str(args.exc_value), text, context=f"thread_{name}")

    sys.excepthook = on_main_thread_crash
    threading.excepthook = on_worker_thread_crash
