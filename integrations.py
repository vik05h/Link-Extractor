"""JDownloader 2 push and file exporters."""

import http.client
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from typing import List, Tuple

import links

log = logging.getLogger(__name__)


def get_jd_folderwatch_dirs() -> List[str]:
    """Find all candidate JDownloader 2 folderwatch directories on the system."""
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "JDownloader 2", "folderwatch"),
        os.path.join(os.environ.get("APPDATA", ""), "JDownloader 2", "folderwatch"),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "JDownloader 2", "folderwatch"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "JDownloader 2", "folderwatch"),
    ]
    valid = []
    for candidate in candidates:
        if os.path.exists(os.path.dirname(candidate)):
            try:
                os.makedirs(candidate, exist_ok=True)
                valid.append(candidate)
            except OSError as error:
                log.info("Cannot use JDownloader folder %s: %s", candidate, error)
    return valid


def _single_line(text: str) -> str:
    """Titles can come from the shared database, and a line break could add crawljob settings."""
    return re.sub(r"[\r\n]+", " ", text or "").strip()


def push_to_jdownloader(
    urls: List[str],
    package_name: str = "FitGirl Repack",
    source_url: str = "",
    port: int = 9666,
    timeout: float = 5.0,
) -> Tuple[bool, str]:
    """Send links to JDownloader 2 over its local API, or through its watch folder if that fails."""
    if not urls:
        return False, "No URLs to push."

    package = _single_line(package_name) or "FitGirl Repack"
    named_urls = links.with_filename_fragments(urls, package)
    form = urllib.parse.urlencode({
        "urls": "\r\n".join(named_urls),
        "package": package,
        "source": source_url or "https://fitgirl-repacks.site/",
    }).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/flash/add",
        data=form,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status in (200, 204):
                return True, f"Successfully pushed {len(named_urls)} links for '{package}' into JDownloader 2!"
            return True, f"Pushed {len(named_urls)} links to JDownloader (Status {response.status})."
    except (OSError, ValueError, http.client.HTTPException) as error:
        log.info("JDownloader API unavailable, trying the watch folder: %s", error)

    for folder in get_jd_folderwatch_dirs()[:1]:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", package).strip("_") or "repack"
        if export_crawljob(os.path.join(folder, f"{safe_name}_{int(time.time())}.crawljob"), named_urls, package):
            return True, f"Pushed {len(named_urls)} links to JDownloader 2 via folderwatch!"
    return False, f"Could not connect to JDownloader 2 on port {port}. Please make sure JDownloader 2 is running."


def export_crawljob(filepath: str, urls: List[str], package_name: str = "FitGirl Repack", auto_start: bool = False) -> bool:
    """Write a JDownloader 2 .crawljob file."""
    package = _single_line(package_name)
    # The format expects a literal backslash-r backslash-n between links on one line.
    joined_links = "\\r\\n".join(links.with_filename_fragments(urls, package))
    lines = [
        f"text={joined_links}",
        f"packageName={package}",
        "enabled=true",
        f"autoStart={'true' if auto_start else 'false'}",
        "forcedStart=false",
        "autoConfirm=true",
    ]
    return _write_text(filepath, "\n".join(lines) + "\n")


def export_json(filepath: str, title: str, source_url: str, urls: List[str], total_size_str: str = "") -> bool:
    """Write extraction results as formatted JSON."""
    named_urls = links.with_filename_fragments(urls, title)
    data = {
        "title": title,
        "source_url": source_url,
        "total_parts": len(named_urls),
        "total_size": total_size_str,
        "urls": named_urls,
    }
    return _write_text(filepath, json.dumps(data, indent=2))


def export_text(filepath: str, urls: List[str], package_name: str = "FitGirl_Repack") -> bool:
    """Write a plain list of links."""
    return _write_text(filepath, "\n".join(links.with_filename_fragments(urls, package_name)) + "\n")


def _write_text(filepath: str, content: str) -> bool:
    try:
        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write(content)
        return True
    except OSError as error:
        log.warning("Could not write %s: %s", filepath, error)
        return False
