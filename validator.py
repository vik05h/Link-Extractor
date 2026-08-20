import os
import re
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any, Union
import threading


@dataclass
class ValidatedLink:
    index: int
    url: str
    is_valid: bool = False
    status_code: int = 0
    content_length: int = 0
    content_length_str: str = "0 B"
    filename: str = ""
    error_message: Optional[str] = None


@dataclass
class ValidationSummary:
    total_links: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    total_bytes: int = 0
    total_size_str: str = "0 B"
    links: List[ValidatedLink] = field(default_factory=list)


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB, TB)."""
    if num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    val = float(num_bytes)
    while val >= 1024.0 and i < len(units) - 1:
        val /= 1024.0
        i += 1
    return f"{val:.2f} {units[i]}" if i >= 2 else f"{val:.0f} {units[i]}"


def validate_single_url(index: int, url: str, timeout: float = 12.0) -> ValidatedLink:
    """
    Perform ultra-fast 1-byte Range GET request to retrieve exact total file size
    and Content-Disposition filename without downloading the file.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Range": "bytes=0-0"
    }

    result = ValidatedLink(index=index, url=url)

    # Fallback filename from URL
    parsed = urllib.parse.urlparse(url)
    path_name = os.path.basename(parsed.path)
    result.filename = path_name or f"part_{index+1}.rar"

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result.status_code = resp.status
            result.is_valid = resp.status in (200, 206, 301, 302, 303, 307, 308)

            # 1. Parse total size from Content-Range (e.g. "bytes 0-0/211526980")
            cr = resp.headers.get("Content-Range", "")
            if cr and "/" in cr:
                total_part = cr.split("/")[-1].strip()
                if total_part.isdigit():
                    result.content_length = int(total_part)
                    result.content_length_str = format_bytes(result.content_length)

            # Fallback to Content-Length if 200 OK without range
            if result.content_length == 0:
                cl = resp.headers.get("Content-Length")
                if cl and cl.isdigit() and int(cl) > 1:
                    result.content_length = int(cl)
                    result.content_length_str = format_bytes(result.content_length)

            # 2. Parse Filename from Content-Disposition
            cd = resp.headers.get("Content-Disposition", "")
            if cd:
                fn_match = re.search(r'filename\*?=(?:UTF-8\'\')?([^\x22\x27;]+)', cd, re.IGNORECASE)
                if fn_match:
                    clean_fn = urllib.parse.unquote(fn_match.group(1).strip('\x22\x27'))
                    if clean_fn:
                        result.filename = clean_fn

    except urllib.error.HTTPError as e:
        result.status_code = e.code
        result.error_message = f"HTTP {e.code}"
        # Fallback to HEAD request if server rejects Range header
        try:
            head_req = urllib.request.Request(url, headers={"User-Agent": headers["User-Agent"]}, method="HEAD")
            with urllib.request.urlopen(head_req, timeout=timeout) as head_resp:
                result.status_code = head_resp.status
                result.is_valid = head_resp.status in (200, 206, 301, 302, 303, 307, 308)
                cl = head_resp.headers.get("Content-Length")
                if cl and cl.isdigit():
                    result.content_length = int(cl)
                    result.content_length_str = format_bytes(result.content_length)
        except Exception:
            result.is_valid = False

    except Exception as e:
        result.is_valid = False
        result.error_message = str(e)

    return result


def validate_links(
    urls: List[str],
    max_workers: int = 15,
    on_progress: Optional[Callable[[int, int, int, str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> ValidationSummary:
    """
    Validate a list of URLs concurrently using ThreadPoolExecutor.
    Callbacks:
      on_progress(validated_count, total_count, total_bytes_so_far, current_total_size_str)
    """
    if not urls:
        return ValidationSummary()

    total = len(urls)
    results = [None] * total
    total_bytes = 0
    validated_count = 0

    with ThreadPoolExecutor(max_workers=min(max_workers, total)) as executor:
        future_to_idx = {
            executor.submit(validate_single_url, idx, url): idx
            for idx, url in enumerate(urls)
        }

        for future in as_completed(future_to_idx):
            if cancel_event and cancel_event.is_set():
                break

            idx = future_to_idx[future]
            try:
                res = future.result()
                results[idx] = res
                if res.is_valid:
                    total_bytes += res.content_length
            except Exception as e:
                results[idx] = ValidatedLink(index=idx, url=urls[idx], is_valid=False, error_message=str(e))

            validated_count += 1
            if on_progress:
                on_progress(validated_count, total, total_bytes, format_bytes(total_bytes))

    # Fill any uncompleted items if cancelled
    valid_links = []
    for i, r in enumerate(results):
        if r is None:
            r = ValidatedLink(index=i, url=urls[i], is_valid=False, error_message="Cancelled")
        valid_links.append(r)

    valid_count = sum(1 for r in valid_links if r.is_valid)
    invalid_count = total - valid_count

    return ValidationSummary(
        total_links=total,
        valid_count=valid_count,
        invalid_count=invalid_count,
        total_bytes=total_bytes,
        total_size_str=format_bytes(total_bytes),
        links=valid_links
    )
