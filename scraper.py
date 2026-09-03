import re
import html
import json
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


def extract_game_cover_image(url: str, page_html: Optional[str] = None) -> str:
    """Extract game cover/thumbnail image URL from FitGirl page HTML."""
    if page_html:
        # 1. Look for wp-post-image or featured image
        img_match = re.search(r'<img[^>]+class=[\x22\x27][^\x22\x27]*wp-post-image[^\x22\x27]*[\x22\x27][^>]+src=[\x22\x27](https?://[^\x22\x27]+)[\x22\x27]', page_html, re.IGNORECASE)
        if img_match:
            return img_match.group(1).strip()

        # 2. Look for any image inside entry-content
        entry_match = re.search(r'<div[^>]*class=[\x22\x27]entry-content[\x22\x27][^>]*>(.*?)</div>', page_html, re.IGNORECASE | re.DOTALL)
        if entry_match:
            first_img = re.search(r'<img[^>]+src=[\x22\x27](https?://[^\x22\x27]+\.(?:jpg|jpeg|png|webp))[\x22\x27]', entry_match.group(1), re.IGNORECASE)
            if first_img:
                return first_img.group(1).strip()

        # 3. Look for og:image meta tag
        og_match = re.search(r'<meta[^>]+property=[\x22\x27]og:image[\x22\x27][^>]+content=[\x22\x27](https?://[^\x22\x27]+)[\x22\x27]', page_html, re.IGNORECASE)
        if og_match:
            return og_match.group(1).strip()

    return ""


def extract_game_slug(url: str, title: str = "") -> str:
    """Extract clean URL slug for game."""
    if "fitgirl-repacks.site" in url:
        parsed = urllib.parse.urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if path_parts:
            return path_parts[-1].lower()
    if title:
        clean = re.sub(r'\[.*?\]|\(.*?\)', '', title)
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', clean.lower()).strip('-')
        if slug:
            return slug
    return "fitgirl-game"


def extract_game_page_pastebins(game_url: str) -> Tuple[List[Dict[str, str]], str, str]:
    """
    Fetch a FitGirl game page and extract all pastebin links with hoster names, game title, and cover image.
    Returns:
      (pastebin_list, game_title, cover_image_url)
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
    cover_image_url = extract_game_cover_image(game_url, page_html)
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

    return results, game_title, cover_image_url


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


def extract_game_info_from_part_urls(urls: List[str]) -> Tuple[str, str]:
    """
    Analyze part filenames (from URL fragments or paths) to infer the game title candidate
    and search query.
    Example: '#Crimson_Desert_Enhanced_--_fitgirl-repacks.site_--_.part01.rar'
             -> ('Crimson Desert Enhanced', 'Crimson Desert Enhanced')
    """
    for u in urls:
        raw_name = ""
        if "#" in u:
            raw_name = u.split("#")[-1]
        else:
            raw_name = u.rstrip("/").split("/")[-1].split("?")[0]

        if not raw_name:
            continue

        raw_name = urllib.parse.unquote(raw_name)
        # Strip archive extension and part markers
        cleaned = re.sub(r'\.part\d+\.(?:rar|zip|7z|bin|iso)$', '', raw_name, flags=re.IGNORECASE)
        cleaned = re.sub(r'\.(?:rar|zip|7z|bin|iso|exe)$', '', cleaned, flags=re.IGNORECASE)

        # Strip fitgirl watermarks
        cleaned = re.sub(r'--_fitgirl-repacks\.site_--.*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'-fitgirl-repacks\.site.*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'_fitgirl_repacks.*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'fitgirl[-_]repacks?.*', '', cleaned, flags=re.IGNORECASE)

        # Normalize separators
        name = re.sub(r'[-_.]+', ' ', cleaned).strip()
        if name and len(name) > 2 and not name.lower().startswith("part"):
            words = name.split()
            candidate = " ".join(w.capitalize() for w in words)
            query = " ".join(words[:3]) if len(words) >= 3 else candidate
            return candidate, query

    return "FitGirl Repack", "FitGirl"


def search_fitgirl_site(query: str, timeout: float = 6.0) -> Optional[Dict[str, str]]:
    """
    Search FitGirl repack WordPress site for a query to locate the official game post and title.
    """
    clean_q = query.strip()
    if not clean_q or clean_q.lower() == "fitgirl":
        return None

    search_url = f"https://fitgirl-repacks.site/?s={urllib.parse.quote(clean_q)}"
    req = urllib.request.Request(
        search_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    matches = re.findall(
        r'<h1[^>]*class=[\x22\x27]entry-title[\x22\x27][^>]*><a[^>]+href=[\x22\x27](https?://fitgirl-repacks\.site/[^\x22\x27]+)[\x22\x27][^>]*>(.*?)</a></h1>',
        page_html,
        re.IGNORECASE | re.DOTALL
    )

    ignored_keywords = ["updates digest", "upcoming repacks", "faq", "troubleshooting", "donations", "repairs"]
    for post_url, raw_title in matches:
        clean_title = clean_title_text(re.sub(r'<[^>]+>', '', raw_title))
        if any(ik in clean_title.lower() for ik in ignored_keywords):
            continue

        slug = post_url.strip("/").split("/")[-1].lower()
        return {
            "title": clean_title,
            "source_url": post_url,
            "slug": slug,
            "image_url": ""
        }

    return None


def search_steam_artwork(query: str, timeout: float = 4.0) -> Optional[Dict[str, str]]:
    """
    Search Steam Store public API for official high-resolution game artwork header.
    Completely free, unblocked Akamai CDN with zero rate-limiting.
    """
    clean_q = query.strip()
    if not clean_q or clean_q.lower() == "fitgirl":
        return None

    url = f"https://store.steampowered.com/api/storesearch/?term={urllib.parse.quote(clean_q)}&l=english&cc=US"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            items = data.get("items", [])
            if items:
                app_id = items[0].get("id")
                app_name = items[0].get("name", clean_q)
                header_url = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg"
                return {
                    "name": app_name,
                    "image_url": header_url,
                    "app_id": str(app_id)
                }
    except Exception:
        pass
    return None


def generate_procedural_banner_svg(title: str) -> str:
    """
    Generate an instant, high-tech stylized SVG data URI banner for games without web artwork.
    """
    clean = html.escape((title or "FitGirl Repack")[:36])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 215" width="460" height="215">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#09121a"/>
      <stop offset="50%" stop-color="#0c252a"/>
      <stop offset="100%" stop-color="#050a0e"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <rect x="20" y="20" width="80" height="22" rx="4" fill="rgba(0, 240, 160, 0.15)" stroke="#00f0a0" stroke-width="1"/>
  <text x="60" y="35" fill="#00f0a0" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle" letter-spacing="1">FITGIRL</text>
  <text x="230" y="115" fill="#ffffff" font-size="18" font-family="sans-serif" font-weight="bold" text-anchor="middle">{clean}</text>
  <text x="230" y="145" fill="rgba(255,255,255,0.6)" font-size="11" font-family="sans-serif" text-anchor="middle">VERIFIED ARCHIVE REPACK</text>
</svg>"""
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)


def resolve_pastebin_metadata(pastebin_url: str, part_urls: List[str]) -> Dict[str, str]:
    """
    Full intelligence pipeline resolving game title, official cover artwork,
    and canonical slug from decrypted pastebin part links.
    """
    candidate_title, search_query = extract_game_info_from_part_urls(part_urls)

    official_title = ""
    source_url = pastebin_url
    slug = ""
    image_url = ""

    # 1. Search FitGirl site for official repack title and canonical slug
    fg_res = search_fitgirl_site(search_query)
    if fg_res:
        official_title = fg_res.get("title", "")
        source_url = fg_res.get("source_url", pastebin_url)
        slug = fg_res.get("slug", "")

    # Fallback title if search failed
    final_title = official_title or candidate_title or "FitGirl Repack"
    final_slug = slug or extract_game_slug(source_url, final_title)

    # 2. Search high-res artwork via Steam CDN
    steam_query = search_query if len(search_query) > 3 else final_title
    steam_res = search_steam_artwork(steam_query)
    if steam_res and steam_res.get("image_url"):
        image_url = steam_res["image_url"]

    # 3. If still no artwork, generate stylized procedural banner
    if not image_url:
        image_url = generate_procedural_banner_svg(final_title)

    return {
        "title": final_title,
        "image_url": image_url,
        "source_url": source_url,
        "slug": final_slug
    }

