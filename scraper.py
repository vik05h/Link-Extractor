import re
import urllib.request
import urllib.parse
from typing import List, Dict, Tuple, Optional, Callable


def detect_url_type(raw_input: str) -> str:
    """
    Detect the type of URL or text entered by the user.
    Returns one of:
      - 'fitgirl_game_page': e.g. https://fitgirl-repacks.site/black-myth-wukong/
      - 'fitgirl_pastebin': e.g. https://paste.fitgirl-repacks.site/?dc64365f494f3ba0#...
      - 'fuckingfast_direct': single https://fuckingfast.co/... link
      - 'raw_links': multiple links containing fuckingfast.co
      - 'unknown': unrecognized input
    """
    text = raw_input.strip()
    if not text:
        return "unknown"

    # Check for multiple URLs in input
    all_urls = re.findall(r'https?://[^\s,]+', text)
    ff_urls = [u for u in all_urls if "fuckingfast.co" in urllib.parse.urlparse(u).netloc]
    if len(ff_urls) > 1:
        return "raw_links"
    elif len(ff_urls) == 1 and len(all_urls) == 1:
        return "fuckingfast_direct"

    # Parse primary URL
    parsed = urllib.parse.urlparse(text)
    host = parsed.netloc.lower()

    if "paste.fitgirl-repacks.site" in host:
        return "fitgirl_pastebin"
    elif "fitgirl-repacks.site" in host:
        return "fitgirl_game_page"
    elif "fuckingfast.co" in host:
        return "fuckingfast_direct"

    # Fallback to substring matching if URL was entered without protocol
    if text.startswith("paste.fitgirl-repacks.site") or "paste.fitgirl-repacks.site" in text.split("#")[0]:
        return "fitgirl_pastebin"
    elif "fitgirl-repacks.site" in text.split("#")[0]:
        return "fitgirl_game_page"
    elif "fuckingfast.co" in text:
        return "fuckingfast_direct"

    return "unknown"


def extract_game_page_pastebins(game_url: str) -> List[Dict[str, str]]:
    """
    Fetch a FitGirl game page and extract all pastebin links with hoster names.
    Returns a list of dicts:
      [{'hoster': 'FuckingFast', 'url': 'https://paste.fitgirl-repacks.site/?...#...', 'label': '...'}, ...]
    """
    # Normalize URL
    if not game_url.startswith("http://") and not game_url.startswith("https://"):
        game_url = "https://" + game_url

    req = urllib.request.Request(
        game_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch FitGirl game page: {e}")

    results = []
    # Pattern matching <li> items with pastebin links and hoster labels
    pattern = r'<a[^>]+href=[\x22\x27](https?://paste\.fitgirl-repacks\.site/[^\x22\x27]+)[\x22\x27][^>]*>(.*?)</a>'
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

    for url, raw_label in matches:
        clean_label = re.sub(r'<[^>]+>', '', raw_label).strip()
        hoster = "Unknown"
        if "fuckingfast" in clean_label.lower():
            hoster = "FuckingFast"
        elif "datanodes" in clean_label.lower():
            hoster = "DataNodes"
        elif "filekeeper" in clean_label.lower():
            hoster = "FileKeeper"
        elif "multiupload" in clean_label.lower():
            hoster = "MultiUpload"
        else:
            hoster = clean_label or "Mirror"

        results.append({
            "hoster": hoster,
            "url": url,
            "label": clean_label
        })

    # If no <li> matches found, search for any pastebin link in the page
    if not results:
        raw_pastes = re.findall(r'https?://paste\.fitgirl-repacks\.site/[^\s\x22\x27<>]+', html)
        for url in raw_pastes:
            results.append({
                "hoster": "FuckingFast" if "fuckingfast" in url.lower() else "Pastebin",
                "url": url,
                "label": "FitGirl Pastebin"
            })

    return results


def extract_links_from_pastebin_html(page_content: str) -> List[str]:
    """
    Extract all fuckingfast.co links from decrypted pastebin HTML or text.
    """
    urls = re.findall(r'https?://(?:www\.)?fuckingfast\.co/[^\s\x22\x27<>]+', page_content)
    seen = set()
    deduped = []
    for u in urls:
        clean_u = u.strip()
        if clean_u not in seen:
            seen.add(clean_u)
            deduped.append(clean_u)
    return deduped
