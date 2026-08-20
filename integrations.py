import os
import re
import json
import urllib.request
import urllib.parse
from typing import List, Optional, Tuple, Dict, Any


def is_jdownloader_running(port: int = 9666, timeout: float = 2.0) -> bool:
    """Check if JDownloader 2 local HTTP server is alive on port 9666."""
    try:
        url = f"http://127.0.0.1:{port}/"
        req = urllib.request.Request(url, headers={"User-Agent": "FitGirlLinkExtractor/3.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="ignore").lower()
            return "jdownloader" in content or resp.status == 200
    except Exception:
        # Also try /flash/ endpoint
        try:
            url = f"http://127.0.0.1:{port}/flash/"
            req = urllib.request.Request(url, headers={"User-Agent": "FitGirlLinkExtractor/3.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 404, 405)
        except Exception:
            return False


def push_to_jdownloader(
    urls: List[str],
    package_name: str = "FitGirl Repack",
    source_url: str = "",
    port: int = 9666,
    timeout: float = 5.0
) -> Tuple[bool, str]:
    """
    Push direct download links directly into JDownloader 2 via local FlashGot/CNL API.
    Returns (success: bool, message: str).
    """
    if not urls:
        return False, "No URLs to push."

    url_data = "\r\n".join(urls)
    endpoint = f"http://127.0.0.1:{port}/flash/add"

    form_data = urllib.parse.urlencode({
        "urls": url_data,
        "package": package_name,
        "source": source_url or "https://fitgirl-repacks.site/"
    }).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=form_data,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status in (200, 204):
                return True, f"Successfully pushed {len(urls)} links into JDownloader 2 LinkGrabber!"
            return True, f"Pushed to JDownloader (Status {resp.status})."
    except urllib.error.URLError as e:
        return False, f"Could not connect to JDownloader 2 on port {port}. Please make sure JDownloader 2 is running."
    except Exception as e:
        return False, f"Push failed: {e}"


def export_crawljob(
    filepath: str,
    urls: List[str],
    package_name: str = "FitGirl Repack",
    auto_start: bool = True
) -> bool:
    """
    Export URLs as a JDownloader 2 .crawljob file.
    """
    try:
        content_lines = [
            f"text={'\\r\\n'.join(urls)}",
            f"packageName={package_name}",
            f"enabled=true",
            f"autoStart={'true' if auto_start else 'false'}",
            f"forcedStart={'false'}",
            f"autoConfirm={'true'}"
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines) + "\n")
        return True
    except Exception:
        return False


def export_json(
    filepath: str,
    title: str,
    source_url: str,
    urls: List[str],
    total_size_str: str = ""
) -> bool:
    """
    Export extraction results as formatted JSON.
    """
    try:
        data = {
            "title": title,
            "source_url": source_url,
            "total_parts": len(urls),
            "total_size": total_size_str,
            "urls": urls
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def export_text(filepath: str, urls: List[str]) -> bool:
    """
    Export URLs as simple text list.
    """
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(urls) + "\n")
        return True
    except Exception:
        return False
