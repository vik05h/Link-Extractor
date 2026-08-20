import json
import urllib.request
import urllib.parse
import webbrowser
from typing import Optional, Dict, Any, Tuple

CURRENT_VERSION = "v3.1.0"
GITHUB_REPO = "vik05h/Link-Extractor"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
FALLBACK_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"


def parse_version(v_str: str) -> tuple:
    """Parse version string like 'v3.1.0' or '3.1.0' into comparable tuple (3, 1, 0)."""
    clean = v_str.strip().lstrip("vV")
    parts = []
    for p in clean.split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_updates(current_version: str = CURRENT_VERSION, timeout: float = 5.0) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Check GitHub Releases for newer version of the application.
    Returns:
      (has_update: bool, release_info: Optional[dict], message: str)
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
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                latest_tag = data.get("tag_name", "")
                release_name = data.get("name", latest_tag)
                release_body = data.get("body", "No changelog provided.")
                html_url = data.get("html_url", FALLBACK_RELEASES_URL)

                # Check downloadable binary assets
                assets = data.get("assets", [])
                download_url = html_url
                for a in assets:
                    if a.get("name", "").endswith(".exe"):
                        download_url = a.get("browser_download_url", html_url)
                        break

                curr_tuple = parse_version(current_version)
                latest_tuple = parse_version(latest_tag)

                release_info = {
                    "current_version": current_version,
                    "latest_version": latest_tag,
                    "name": release_name,
                    "body": release_body,
                    "html_url": html_url,
                    "download_url": download_url,
                    "published_at": data.get("published_at", "")
                }

                if latest_tuple > curr_tuple:
                    return True, release_info, f"New version {latest_tag} is available!"
                else:
                    return False, release_info, f"You are running the latest version ({current_version})."

            return False, None, f"GitHub returned status {resp.status}."

    except urllib.error.HTTPError as he:
        if he.code == 404:
            return False, None, "No releases published yet on GitHub."
        return False, None, f"HTTP Error {he.code}: Could not check for updates."
    except Exception as e:
        return False, None, f"Update check failed: {e}"


def open_release_page(url: Optional[str] = None):
    """Open release page or latest download URL in default web browser."""
    target = url or FALLBACK_RELEASES_URL
    webbrowser.open(target)
