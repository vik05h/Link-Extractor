import os
import re
import json
import time
import urllib.request
import urllib.parse
from typing import List, Optional, Tuple, Dict, Any


def get_jd_folderwatch_dirs() -> List[str]:
    """Find all candidate JDownloader 2 folderwatch directories on the system."""
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "JDownloader 2", "folderwatch"),
        os.path.join(os.environ.get("APPDATA", ""), "JDownloader 2", "folderwatch"),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "JDownloader 2", "folderwatch"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "JDownloader 2", "folderwatch"),
    ]
    valid = []
    for c in candidates:
        parent = os.path.dirname(c)
        if os.path.exists(parent):
            try:
                os.makedirs(c, exist_ok=True)
                valid.append(c)
            except Exception:
                pass
    return valid


def format_urls_for_jdownloader(urls: List[str], package_name: str = "FitGirl_Repack") -> List[str]:
    """
    Ensure every direct download URL has a '#filename.partXX.rar' fragment.
    This guarantees JDownloader 2 treats it as a direct archive file and never
    triggers 'Deep Link Analysis' or 'Nothing Found' dialogs.
    """
    safe_pkg = re.sub(r'[^a-zA-Z0-9_-]', '_', package_name).strip('_') or "FitGirl_Repack"
    formatted = []
    for i, u in enumerate(urls):
        clean = u.strip()
        if not clean:
            continue
        if "#" in clean:
            formatted.append(clean)
        else:
            formatted.append(f"{clean}#{safe_pkg}.part{i+1:03d}.rar")
    return formatted


def is_jdownloader_running(port: int = 9666, timeout: float = 2.0) -> bool:
    """Check if JDownloader 2 local HTTP server is alive on port 9666."""
    try:
        url = f"http://127.0.0.1:{port}/"
        req = urllib.request.Request(url, headers={"User-Agent": "FitGirlLinkExtractor/3.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="ignore").lower()
            return "jdownloader" in content or resp.status == 200
    except Exception:
        try:
            url = f"http://127.0.0.1:{port}/flash/"
            req = urllib.request.Request(url, headers={"User-Agent": "FitGirlLinkExtractor/3.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 404, 405)
        except Exception:
            return bool(get_jd_folderwatch_dirs())


def push_to_jdownloader(
    urls: List[str],
    package_name: str = "FitGirl Repack",
    source_url: str = "",
    port: int = 9666,
    timeout: float = 5.0
) -> Tuple[bool, str]:
    """
    Push direct download links into JDownloader 2 via dual channels:
    1. Local FlashGot/CNL HTTP API (port 9666)
    2. Direct .crawljob write to JDownloader 2 folderwatch directory
    Returns (success: bool, message: str).
    """
    if not urls:
        return False, "No URLs to push."

    # Format URLs with #filename.rar fragments so JDownloader recognizes them as archives
    clean_urls = format_urls_for_jdownloader(urls, package_name)
    url_data = "\r\n".join(clean_urls)
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
                return True, f"Successfully pushed {len(clean_urls)} links for '{package_name}' into JDownloader 2!"
            return True, f"Pushed {len(clean_urls)} links to JDownloader (Status {resp.status})."
    except urllib.error.URLError:
        return False, f"Could not connect to JDownloader 2 on port {port}. Please make sure JDownloader 2 is running."
    except Exception as e:
        return False, f"Push failed: {e}"


def export_crawljob(
    filepath: str,
    urls: List[str],
    package_name: str = "FitGirl Repack",
    auto_start: bool = False
) -> bool:
    """
    Export URLs as a JDownloader 2 .crawljob file.
    """
    try:
        clean_urls = format_urls_for_jdownloader(urls, package_name)
        content_lines = [
            f"text={'\\r\\n'.join(clean_urls)}",
            f"packageName={package_name}",
            "enabled=true",
            f"autoStart={'true' if auto_start else 'false'}",
            "forcedStart=false",
            "autoConfirm=true"
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
        clean_urls = format_urls_for_jdownloader(urls, title)
        data = {
            "title": title,
            "source_url": source_url,
            "total_parts": len(clean_urls),
            "total_size": total_size_str,
            "urls": clean_urls
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def export_text(filepath: str, urls: List[str], package_name: str = "FitGirl_Repack") -> bool:
    """
    Export URLs as simple text list with #filename.rar fragments.
    """
    try:
        clean_urls = format_urls_for_jdownloader(urls, package_name)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(clean_urls) + "\n")
        return True
    except Exception:
        return False
