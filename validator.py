import os
import re
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


@dataclass
class ValidatedLink:
    index: int
    url: str
    filename: str = "Unknown"
    content_length_bytes: int = 0
    content_length_str: str = "0 B"
    status_code: int = 0
    is_valid: bool = False
    error: Optional[str] = None


@dataclass
class ValidationSummary:
    total_links: int = 0
    valid_count: int = 0
    failed_count: int = 0
    total_bytes: int = 0
    total_size_str: str = "0 B"
    links: List[ValidatedLink] = field(default_factory=list)


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

    # Fallback filename from URL or fragment
    parsed = urllib.parse.urlparse(url)
    clean_url = url.split("#")[0]
    fallback_name = parsed.fragment or os.path.basename(parsed.path) or f"part_{index+1}.rar"
    result.filename = fallback_name

    req = urllib.request.Request(clean_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result.status_code = resp.status
            result.is_valid = resp.status in (200, 206)

            # 1. Parse exact filename from Content-Disposition header
            disp = resp.headers.get("Content-Disposition", "")
            if disp:
                # Check for RFC 5987 UTF-8 filename*=UTF-8''filename.ext
                utf8_match = re.search(r"filename\*=UTF-8''([^;]+)", disp, re.IGNORECASE)
                if utf8_match:
                    result.filename = urllib.parse.unquote(utf8_match.group(1))
                else:
                    # Standard filename="filename.ext"
                    fn_match = re.search(r'filename=["\x27]?([^"\x27;]+)["\x27]?', disp, re.IGNORECASE)
                    if fn_match:
                        result.filename = fn_match.group(1).strip()

            # 2. Parse total repack file size from Content-Range or Content-Length
            cr_header = resp.headers.get("Content-Range", "")
            if cr_header:
                cr_match = re.search(r'/(\d+)', cr_header)
                if cr_match:
                    result.content_length_bytes = int(cr_match.group(1))
                    result.content_length_str = format_bytes(result.content_length_bytes)

            if result.content_length_bytes == 0:
                cl_header = resp.headers.get("Content-Length", "")
                if cl_header and cl_header.isdigit() and int(cl_header) > 1:
                    result.content_length_bytes = int(cl_header)
                    result.content_length_str = format_bytes(result.content_length_bytes)

    except urllib.error.HTTPError as he:
        result.status_code = he.code
        result.error = f"HTTP {he.code}"
        result.is_valid = False
    except Exception as e:
        result.error = str(e)
        result.is_valid = False

    return result


def validate_links(
    urls: List[str],
    max_workers: int = 15,
    on_progress: Optional[Callable[[int, int, ValidatedLink], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> ValidationSummary:
    """
    Concurrently validate all direct download links and calculate total repack size.
    Uses 1-byte Range GET requests (only 1 byte per part used).
    """
    summary = ValidationSummary(total_links=len(urls))
    if not urls:
        return summary

    results: List[Optional[ValidatedLink]] = [None] * len(urls)
    completed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(validate_single_url, idx, url): idx
            for idx, url in enumerate(urls)
        }

        for future in as_completed(future_to_idx):
            if cancel_event and cancel_event.is_set():
                break

            idx = future_to_idx[future]
            try:
                item = future.result()
                results[idx] = item
                completed_count += 1

                if on_progress:
                    on_progress(completed_count, len(urls), item)

            except Exception as e:
                err_item = ValidatedLink(index=idx, url=urls[idx], error=str(e))
                results[idx] = err_item

    # Assemble summary
    final_links = [r for r in results if r is not None]
    summary.links = final_links
    summary.valid_count = sum(1 for r in final_links if r.is_valid)
    summary.failed_count = sum(1 for r in final_links if not r.is_valid)
    summary.total_bytes = sum(r.content_length_bytes for r in final_links if r.is_valid)
    summary.total_size_str = format_bytes(summary.total_bytes)

    return summary
