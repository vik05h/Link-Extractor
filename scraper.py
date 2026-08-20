import re
import html
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


def clean_title_text(raw_text: str) -> str:
    """Clean HTML entities and normalize smart quotes/dashes."""
    text = html.unescape(raw_text)
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = text.replace('\u2013', "–").replace('\u2014', "—")
    text = text.replace('&#8217;', "'").replace('&#8211;', "–").replace('&#8212;', "—")
    text = text.replace('&amp;', '&')
    return text.strip()


def extract_game_title(url: str, page_html: Optional[str] = None) -> str:
    """Extract human-readable game title from FitGirl URL or page HTML with full entity unescaping."""
    if page_html:
        h1_match = re.search(r'<h1[^>]*class=[\x22\x27]entry-title[\x22\x27][^>]*>(.*?)</h1>', page_html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            raw_text = re.sub(r'<[^>]+>', '', h1_match.group(1))
            clean = clean_title_text(raw_text)
            if clean:
                return clean

        title_match = re.search(r'<title>(.*?)</title>', page_html, re.IGNORECASE)
        if title_match:
            t = clean_title_text(title_match.group(1)).split('- FitGirl')[0].split('|')[0].strip()
            if t:
                return t

    # Fallback to URL path slug
    parsed = urllib.parse.urlparse(url)
    slug = parsed.path.strip('/').split('/')[-1]
    if slug:
        words = [w.capitalize() for w in re.split(r'[-_]', slug) if w]
        return " ".join(words)
    return "FitGirl Repack"


def extract_game_page_pastebins(game_url: str) -> Tuple[List[Dict[str, str]], str]:
    """
    Fetch a FitGirl game page and extract all pastebin links with hoster names and game title.
    Returns:
      (pastebin_list, game_title)
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
            content_bytes = resp.read()
            # Try utf-8 first, fallback to windows-1252 / latin-1
            try:
                page_html = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                page_html = content_bytes.decode("windows-1252", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch FitGirl game page: {e}")

    game_title = extract_game_title(game_url, page_html)
    results = []

    pattern = r'<a[^>]+href=[\x22\x27](https?://paste\.fitgirl-repacks\.site/[^\x22\x27]+)[\x22\x27][^>]*>(.*?)</a>'
    matches = re.findall(pattern, page_html, re.IGNORECASE | re.DOTALL)

    for url, raw_label in matches:
        clean_label = clean_title_text(re.sub(r'<[^>]+>', '', raw_label))
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

    if not results:
        raw_pastes = re.findall(r'https?://paste\.fitgirl-repacks\.site/[^\s\x22\x27<>]+', page_html)
        for url in raw_pastes:
            results.append({
                "hoster": "FuckingFast" if "fuckingfast" in url.lower() else "Pastebin",
                "url": url,
                "label": "FitGirl Pastebin"
            })

    return results, game_title


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
