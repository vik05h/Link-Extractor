"""Community Issue Center: public bug reports, votes, comments and moderation.

Moderation is enforced by the database rules, not here. The admin key is sent to the
server with each change and the server decides, so nothing on a user's machine can
grant admin powers. The local file only holds reports still waiting to be delivered.
"""

import logging
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import firebase_client
import game_records
import utils
from firebase_client import FirebaseError, safe_key
from version import APP_VERSION

log = logging.getLogger(__name__)

REPORTS_PATH = "reports"
SCREENSHOTS_PATH = "report_screenshots"
REPORT_SCREENSHOT_KEY = "report"
MAX_SCREENSHOT_CHARS = 800 * 1024
VALID_STATUSES = {"open", "investigating", "fixed", "closed"}

_SCREENSHOT_PREFIX = re.compile(r"^data:image/(?:jpeg|png|webp|gif);base64,")


@dataclass
class SubmitResult:
    outcome: str  # "sent" | "queued" | "duplicate" | "invalid"
    message: str
    report_id: str = ""
    record: Optional[Dict[str, Any]] = None


def _local_file() -> str:
    return os.path.join(utils.get_app_data_dir(), "community_reports.json")


def _load_local_reports() -> Dict[str, Any]:
    try:
        with open(_local_file(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        log.warning("Ignoring unreadable local reports: %s", error)
        return {}
    return data if isinstance(data, dict) else {}


def _save_local_reports(reports: Dict[str, Any]) -> None:
    try:
        utils.write_json_atomic(_local_file(), reports)
    except OSError as error:
        log.warning("Could not save local reports: %s", error)


def _screenshot_problem(data: Optional[str]) -> str:
    """Why a screenshot cannot be accepted, or an empty string if it is fine."""
    if not data:
        return ""
    if not isinstance(data, str) or not _SCREENSHOT_PREFIX.match(data):
        return "The attachment is not a supported image."
    if len(data) > MAX_SCREENSHOT_CHARS:
        return "The screenshot is too large. Please attach a smaller image (800 KB at most)."
    return ""


def _attach_screenshot(payload: Dict[str, Any], report_id: str, key: str, data: Optional[str], auth: Optional[str] = None) -> None:
    """Store a screenshot apart from the report so listing reports stays small.

    Until the updated database rules are in place that path is refused, and the
    screenshot stays inside the report as it always has.
    """
    if not data:
        return
    try:
        firebase_client.request(f"{SCREENSHOTS_PATH}/{report_id}/{key}", "PUT", data, auth=auth)
        payload["has_screenshot"] = True
    except FirebaseError as error:
        if not error.denied:
            raise
        payload["screenshot_data"] = data


def _send_report(report: Dict[str, Any]) -> None:
    """Deliver one report. Raises FirebaseError if the server does not take it."""
    payload = {key: value for key, value in report.items() if key not in ("screenshot_data", "pending_upload")}
    _attach_screenshot(payload, report["id"], REPORT_SCREENSHOT_KEY, report.get("screenshot_data"))
    firebase_client.request(f"{REPORTS_PATH}/{report['id']}", "PUT", payload)


def _normalize(report_id: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    report = {**raw, "id": report_id}
    comments = report.get("comments")
    if isinstance(comments, dict):
        comments = list(comments.values())
    if not isinstance(comments, list):
        comments = []
    comments = [comment for comment in comments if isinstance(comment, dict)]
    comments.sort(key=lambda comment: comment.get("created_at", ""))
    report["comments"] = comments
    report["comments_count"] = len(comments)
    return report


def fetch_all_reports() -> Tuple[bool, List[Dict[str, Any]], str]:
    """All reports, with the server as the source of truth. Returns (reached_server, reports, message)."""
    reached = True
    cloud: Dict[str, Any] = {}
    try:
        data = firebase_client.request(REPORTS_PATH, timeout=8.0)
        if isinstance(data, dict):
            cloud = data
    except FirebaseError as error:
        reached = False
        log.warning("Could not load reports: %s", error)

    local = _load_local_reports()
    if reached:
        local = _deliver_and_prune(local, cloud)

    merged = {rid: _normalize(rid, item) for rid, item in cloud.items() if isinstance(item, dict)}
    for rid, item in local.items():
        if rid not in merged and isinstance(item, dict):
            report = _normalize(rid, item)
            report["local_only"] = not item.get("pending_upload")
            merged[rid] = report

    reports = sorted(merged.values(), key=lambda report: report.get("created_at", ""), reverse=True)
    message = f"Loaded {len(reports)} reports" if reached else "Could not reach the server. Showing reports saved on this PC."
    return reached, reports, message


def _deliver_and_prune(local: Dict[str, Any], cloud: Dict[str, Any]) -> Dict[str, Any]:
    """Send waiting reports, and drop local copies the server already has so they cannot override it."""
    remaining = dict(local)
    for rid, item in local.items():
        if rid in cloud:
            del remaining[rid]
        elif isinstance(item, dict) and item.get("pending_upload"):
            try:
                _send_report({**item, "id": rid})
            except FirebaseError as error:
                log.info("Report %s still not delivered: %s", rid, error)
                continue
            cloud[rid] = {key: value for key, value in item.items() if key not in ("screenshot_data", "pending_upload")}
            del remaining[rid]
    if remaining != local:
        _save_local_reports(remaining)
    return remaining


def _compute_similarity(text1: str, text2: str) -> float:
    """Word overlap between two subjects, with basic stemming."""

    def tokenize(text: str) -> set:
        words = set()
        for word in re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower()).split():
            if len(word) <= 2:
                continue
            if word.endswith("ing") and len(word) > 5:
                word = word[:-3]
            elif word.endswith("s") and len(word) > 4:
                word = word[:-1]
            elif word.endswith("ed") and len(word) > 4:
                word = word[:-2]
            words.add(word)
        return words

    first, second = tokenize(text1), tokenize(text2)
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def find_duplicate_report(subject: str, reports: List[Dict[str, Any]], threshold: float = 0.55) -> Optional[Dict[str, Any]]:
    """The existing report with this or a very similar subject, if any."""
    clean = subject.strip().lower()
    if len(clean) < 4:
        return None
    best, best_score = None, 0.0
    for report in reports:
        other = str(report.get("subject", "")).strip().lower()
        if not other:
            continue
        if clean == other or clean in other or other in clean:
            return report
        score = _compute_similarity(clean, other)
        if score >= threshold and score > best_score:
            best, best_score = report, score
    return best


def submit_user_report(
    subject: str,
    category: str,
    description: str,
    screenshot_data: Optional[str] = None,
    telemetry: Optional[Dict[str, Any]] = None,
    force_create: bool = False,
) -> SubmitResult:
    """Send a new report, or add a vote if the same issue is already reported."""
    clean_subject = (subject or "").strip()
    if not clean_subject:
        return SubmitResult("invalid", "Subject cannot be empty.")
    problem = _screenshot_problem(screenshot_data)
    if problem:
        return SubmitResult("invalid", problem)

    if not force_create:
        _, existing, _ = fetch_all_reports()
        duplicate = find_duplicate_report(clean_subject, existing)
        if duplicate:
            ok, count = increment_report_affected(duplicate["id"])
            if ok:
                duplicate["affected_users_count"] = count
            return SubmitResult(
                "duplicate",
                "This issue is already reported. Your vote was added to help prioritize it.",
                duplicate["id"],
                duplicate,
            )

    report_id = f"rep_{int(time.time())}_{os.urandom(3).hex()}"
    report: Dict[str, Any] = {
        "id": report_id,
        "subject": clean_subject[:150],
        "category": (category or "Bug Report").strip()[:50],
        "description": (description or "").strip()[:3000],
        "status": "open",
        "affected_users_count": 1,
        "created_at": game_records.utc_now_iso(),
        "app_version": APP_VERSION,
        "os_info": sys.platform,
        "telemetry": telemetry or {},
    }
    if screenshot_data:
        report["screenshot_data"] = screenshot_data

    try:
        _send_report(report)
    except FirebaseError as error:
        log.warning("Report not delivered yet: %s", error)
        local = _load_local_reports()
        local[report_id] = {**report, "pending_upload": True}
        _save_local_reports(local)
        return SubmitResult(
            "queued",
            "Your report could not be sent right now. It is saved on this PC and will be sent automatically later.",
            report_id,
            local[report_id],
        )

    sent = {key: value for key, value in report.items() if key != "screenshot_data"}
    if screenshot_data:
        sent["has_screenshot"] = True
    return SubmitResult("sent", "Report submitted. Thank you for helping improve Link Extractor.", report_id, sent)


def increment_report_affected(report_id: str) -> Tuple[bool, int]:
    """Add one vote using a server-side increment, so simultaneous votes are all counted."""
    rid = safe_key(report_id)
    if not rid:
        return False, 0
    try:
        count = firebase_client.request(
            f"{REPORTS_PATH}/{rid}/affected_users_count", "PUT", {".sv": {"increment": 1}}, timeout=4.0
        )
    except FirebaseError as error:
        log.info("Vote not counted: %s", error)
        return False, 0
    return True, count if isinstance(count, int) else 0


def get_screenshot(report_id: str, key: str) -> str:
    """Download one screenshot when someone asks to see it."""
    rid, screenshot = safe_key(report_id), safe_key(key)
    if not rid or not screenshot:
        return ""
    try:
        data = firebase_client.request(f"{SCREENSHOTS_PATH}/{rid}/{screenshot}", timeout=15.0)
    except FirebaseError as error:
        log.info("Could not load screenshot: %s", error)
        return ""
    return data if isinstance(data, str) and _SCREENSHOT_PREFIX.match(data) else ""


def verify_admin_key(candidate: str) -> Tuple[bool, str]:
    """Ask the server whether this key has admin rights. Only the database owner's secret does."""
    key = (candidate or "").strip()
    if not key:
        return False, "Please enter the admin key."
    try:
        firebase_client.request(".settings/rules", auth=key, timeout=6.0)
    except FirebaseError as error:
        if error.unreachable:
            return False, "Could not reach the database to check the key. Please try again."
        return False, "The database did not accept this key."
    return True, "Admin access granted."


def update_report(report_id: str, new_status: str, admin_remark: str, admin_key: str) -> Tuple[bool, str]:
    """Change a report's status and remark. The server decides whether the key is allowed."""
    rid = safe_key(report_id)
    status = (new_status or "").strip().lower()
    if not rid:
        return False, "Invalid report."
    if status not in VALID_STATUSES:
        return False, f"Unknown status: {new_status}"
    changes = {"status": status, "admin_remark": (admin_remark or "").strip(), "updated_at": game_records.utc_now_iso()}
    try:
        firebase_client.request(f"{REPORTS_PATH}/{rid}", "PATCH", changes, auth=admin_key)
    except FirebaseError as error:
        return False, _refusal(error)
    return True, f"Report updated to {status}."


def delete_report(report_id: str, admin_key: str) -> Tuple[bool, str]:
    """Permanently delete a report and its screenshots. The server decides whether the key is allowed."""
    rid = safe_key(report_id)
    if not rid:
        return False, "Invalid report."
    try:
        firebase_client.request(f"{REPORTS_PATH}/{rid}", "DELETE", auth=admin_key)
        firebase_client.request(f"{SCREENSHOTS_PATH}/{rid}", "DELETE", auth=admin_key)
    except FirebaseError as error:
        return False, _refusal(error)
    return True, "Report deleted."


def add_comment(
    report_id: str,
    text: str,
    author_type: str = "gamer",
    author_name: str = "",
    screenshot_data: Optional[str] = None,
    admin_key: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Add a reply. Returns (success, comment id or error message, comment)."""
    rid = safe_key(report_id)
    if not rid:
        return False, "Invalid report.", None
    clean_text = (text or "").strip()
    if not clean_text and not screenshot_data:
        return False, "Comment text or attachment cannot be empty.", None
    problem = _screenshot_problem(screenshot_data)
    if problem:
        return False, problem, None

    kind = (author_type or "gamer").lower().strip()
    if kind not in ("admin", "reporter", "gamer"):
        kind = "gamer"
    auth = None
    if kind == "admin":
        if not admin_key:
            return False, "Admin access is required to post as admin.", None
        auth = admin_key

    comment_id = f"c_{int(time.time())}_{os.urandom(3).hex()}"
    comment: Dict[str, Any] = {
        "id": comment_id,
        "author_type": kind,
        "author_name": (author_name or ("Admin" if kind == "admin" else "Gamer"))[:50],
        "text": clean_text[:3000],
        "created_at": game_records.utc_now_iso(),
        "app_version": APP_VERSION,
    }
    try:
        _attach_screenshot(comment, rid, comment_id, screenshot_data, auth=auth)
        firebase_client.request(f"{REPORTS_PATH}/{rid}/comments/{comment_id}", "PUT", comment, auth=auth)
    except FirebaseError as error:
        return False, _refusal(error), None
    return True, comment_id, comment


def delete_comment(report_id: str, comment_id: str, admin_key: str) -> Tuple[bool, str]:
    """Delete one reply and its screenshot. The server decides whether the key is allowed."""
    rid, cid = safe_key(report_id), safe_key(comment_id)
    if not rid or not cid:
        return False, "Invalid report or comment."
    try:
        firebase_client.request(f"{REPORTS_PATH}/{rid}/comments/{cid}", "DELETE", auth=admin_key)
        firebase_client.request(f"{SCREENSHOTS_PATH}/{rid}/{cid}", "DELETE", auth=admin_key)
    except FirebaseError as error:
        return False, _refusal(error)
    return True, "Comment deleted."


def _refusal(error: FirebaseError) -> str:
    if error.denied:
        return "The server refused this change. Check your admin key."
    if error.unreachable:
        return "Could not reach the server. Please try again."
    return f"The server could not complete this change (HTTP {error.status})."
