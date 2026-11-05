"""Check direct links with 1-byte Range requests and add up the total repack size.

A link gets one of three verdicts. "alive" means the file is there. "dead" means the
server said it is gone. "unknown" means we could not tell (a timeout, a rate limit, a
server error), so the link must not be thrown away and must not count as verified.
"""

import http.client
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, List, Optional

log = logging.getLogger(__name__)

ALIVE = "alive"
DEAD = "dead"
UNKNOWN = "unknown"

RETRY_WORKERS = 4

_TEMPORARY_STATUS_CODES = {408, 425, 429}
_NOT_A_FILE_CONTENT_TYPES = ("text/", "application/json", "application/xhtml")
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class ValidatedLink:
    index: int
    url: str
    filename: str = "Unknown"
    content_length_bytes: int = 0
    content_length_str: str = "0 B"
    status_code: int = 0
    verdict: str = UNKNOWN
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.verdict == ALIVE


@dataclass
class ValidationSummary:
    total_links: int = 0
    valid_count: int = 0
    dead_count: int = 0
    unknown_count: int = 0
    total_bytes: int = 0
    total_size_str: str = "0 B"
    cancelled: bool = False
    links: List[ValidatedLink] = field(default_factory=list)

    @property
    def failed_count(self) -> int:
        return self.dead_count + self.unknown_count


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable B, KB, MB, GB, TB string."""
    if num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    val = float(num_bytes)
    while val >= 1024.0 and i < len(units) - 1:
        val /= 1024.0
        i += 1
    return f"{val:.2f} {units[i]}" if i >= 2 else f"{val:.0f} {units[i]}"


def _sanitize_filename(name: str) -> str:
    """Make a filename from a web header safe to display and to use on disk."""
    base = os.path.basename(name.replace("\\", "/"))
    clean = _UNSAFE_FILENAME_CHARS.sub("_", base).strip(" .")
    return clean or "Unknown"


def _filename_from_header(disposition: str) -> Optional[str]:
    utf8 = re.search(r"filename\*=UTF-8''([^;]+)", disposition, re.IGNORECASE)
    if utf8:
        return urllib.parse.unquote(utf8.group(1))
    plain = re.search(r'filename=["\x27]?([^"\x27;]+)["\x27]?', disposition, re.IGNORECASE)
    return plain.group(1).strip() if plain else None


def validate_single_url(index: int, url: str, timeout: float = 12.0) -> ValidatedLink:
    """Ask for 1 byte to learn whether a part exists, its size and its filename."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Range": "bytes=0-0",
    }
    result = ValidatedLink(index=index, url=url)

    parsed = urllib.parse.urlparse(url)
    result.filename = _sanitize_filename(parsed.fragment or os.path.basename(parsed.path) or f"part_{index + 1}.rar")

    req = urllib.request.Request(url.split("#")[0], headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result.status_code = response.status
            content_type = (response.headers.get("Content-Type") or "").lower()

            if content_type.startswith(_NOT_A_FILE_CONTENT_TYPES):
                # Hosters often answer an expired link with a normal web page and status 200.
                result.verdict = DEAD
                result.error = "The server returned a web page instead of a file"
                return result

            result.verdict = ALIVE
            disposition = response.headers.get("Content-Disposition", "")
            header_name = _filename_from_header(disposition) if disposition else None
            if header_name:
                result.filename = _sanitize_filename(header_name)

            content_range = re.search(r"/(\d+)", response.headers.get("Content-Range", ""))
            content_length = response.headers.get("Content-Length", "")
            if content_range:
                result.content_length_bytes = int(content_range.group(1))
            elif content_length.isdigit() and int(content_length) > 1:
                result.content_length_bytes = int(content_length)
            if result.content_length_bytes:
                result.content_length_str = format_bytes(result.content_length_bytes)

    except urllib.error.HTTPError as error:
        result.status_code = error.code
        result.error = f"HTTP {error.code}"
        is_gone = 400 <= error.code < 500 and error.code not in _TEMPORARY_STATUS_CODES
        result.verdict = DEAD if is_gone else UNKNOWN
    except (OSError, ValueError, http.client.HTTPException) as error:
        result.error = str(error)
        result.verdict = UNKNOWN

    return result


def _run_pass(
    urls: List[str],
    indexes: List[int],
    results: List[Optional[ValidatedLink]],
    max_workers: int,
    report: Callable[[ValidatedLink], None],
    cancel_event: Optional[threading.Event],
) -> bool:
    """Check the given links. Returns False if cancelled, without waiting for queued ones."""
    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="validator")
    try:
        futures = {executor.submit(validate_single_url, index, urls[index]): index for index in indexes}
        for future in as_completed(futures):
            if cancel_event and cancel_event.is_set():
                return False
            index = futures[future]
            try:
                item = future.result()
            except Exception as error:
                # One odd link must not throw away the checks for all the others.
                log.exception("Could not check a link")
                item = ValidatedLink(index=index, url=urls[index], verdict=UNKNOWN, error=str(error))
            results[index] = item
            report(item)
            if cancel_event and cancel_event.is_set():
                return False
        return True
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def validate_links(
    urls: List[str],
    max_workers: int = 15,
    on_progress: Optional[Callable[[int, int, ValidatedLink], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> ValidationSummary:
    """Check all links concurrently. Links we could not judge get one more try, more gently."""
    summary = ValidationSummary(total_links=len(urls))
    if not urls:
        return summary
    if cancel_event and cancel_event.is_set():
        summary.cancelled = True
        return summary

    results: List[Optional[ValidatedLink]] = [None] * len(urls)
    completed = 0

    def report_first_pass(item: ValidatedLink) -> None:
        nonlocal completed
        completed += 1
        if on_progress:
            on_progress(completed, len(urls), item)

    def report_retry(item: ValidatedLink) -> None:
        if on_progress:
            on_progress(len(urls), len(urls), item)

    finished = _run_pass(urls, list(range(len(urls))), results, max_workers, report_first_pass, cancel_event)
    if finished:
        retry = [index for index, item in enumerate(results) if item and item.verdict == UNKNOWN]
        if retry:
            log.info("Retrying %d links that could not be checked", len(retry))
            finished = _run_pass(urls, retry, results, min(RETRY_WORKERS, max_workers), report_retry, cancel_event)

    summary.cancelled = not finished
    summary.links = [item for item in results if item is not None]
    summary.valid_count = sum(1 for item in summary.links if item.verdict == ALIVE)
    summary.dead_count = sum(1 for item in summary.links if item.verdict == DEAD)
    summary.unknown_count = sum(1 for item in summary.links if item.verdict == UNKNOWN)
    summary.total_bytes = sum(item.content_length_bytes for item in summary.links if item.verdict == ALIVE)
    summary.total_size_str = format_bytes(summary.total_bytes)
    return summary
