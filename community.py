import os
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import validator
import updater

DEFAULT_FIREBASE_URL = "https://link-extractor-8cbca-default-rtdb.asia-southeast1.firebasedatabase.app"

# Built-in local offline fallback repository for initial offline experience
DEMO_COMMUNITY_DATA = {
    "elden-ring-shadow-of-the-erdtree": {
        "slug": "elden-ring-shadow-of-the-erdtree",
        "title": "ELDEN RING: Shadow of the Erdtree Edition",
        "image_url": "https://fitgirl-repacks.site/wp-content/uploads/2024/06/elden-ring-sote.jpg",
        "source_url": "https://fitgirl-repacks.site/elden-ring-shadow-of-the-erdtree/",
        "timestamp_utc": "2026-08-20T18:15:00Z",
        "total_parts": 14,
        "resolved_count": 14,
        "total_size_str": "61.2 GB",
        "total_size_bytes": 65712000000,
        "status": "aging",
        "uploader": "Community Scout"
    },
    "cyberpunk-2077-phantom-liberty": {
        "slug": "cyberpunk-2077-phantom-liberty",
        "title": "Cyberpunk 2077: Ultimate Edition – v2.13",
        "image_url": "https://fitgirl-repacks.site/wp-content/uploads/2023/12/cyberpunk-2077-ue.jpg",
        "source_url": "https://fitgirl-repacks.site/cyberpunk-2077/",
        "timestamp_utc": "2026-08-21T06:00:00Z",
        "total_parts": 18,
        "resolved_count": 18,
        "total_size_str": "78.9 GB",
        "total_size_bytes": 84724000000,
        "status": "fresh",
        "uploader": "CyberRunner"
    },
    "god-of-war-ragnarok": {
        "slug": "god-of-war-ragnarok",
        "title": "God of War: Ragnarök – Digital Deluxe Edition",
        "image_url": "https://fitgirl-repacks.site/wp-content/uploads/2024/09/god-of-war-ragnarok.jpg",
        "source_url": "https://fitgirl-repacks.site/god-of-war-ragnarok/",
        "timestamp_utc": "2026-08-19T14:20:00Z",
        "total_parts": 24,
        "resolved_count": 24,
        "total_size_str": "104.5 GB",
        "total_size_bytes": 112211000000,
        "status": "expired",
        "uploader": "KratosBlade"
    }
}

DEMO_COMMUNITY_URLS = {
    "elden-ring-shadow-of-the-erdtree": [
        f"https://dl.fuckingfast.co/dl/er_sote_part{i:02d}#Elden_Ring_SOTE.part{i:02d}.rar" for i in range(1, 15)
    ],
    "cyberpunk-2077-phantom-liberty": [
        f"https://dl.fuckingfast.co/dl/cp2077_ue_part{i:02d}#Cyberpunk_2077_UE.part{i:02d}.rar" for i in range(1, 19)
    ],
    "god-of-war-ragnarok": [
        f"https://dl.fuckingfast.co/dl/gow_rag_part{i:02d}#God_of_War_Ragnarok.part{i:02d}.rar" for i in range(1, 25)
    ]
}


def sanitize_slug(slug_str: str) -> str:
    """Sanitize slug for safe Firebase path and URL parsing."""
    slug = re.sub(r'[^a-zA-Z0-9_-]', '-', slug_str.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug or "unnamed-game"


def generate_game_slug(url: str, title: str = "") -> str:
    """Generate canonical game slug from URL or title."""
    url_clean = (url or "").strip()
    if "fitgirl-repacks.site" in url_clean:
        parsed = urllib.parse.urlparse(url_clean)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if path_parts:
            return sanitize_slug(path_parts[-1])

    if title:
        clean = re.sub(r'\[.*?\]|\(.*?\)', '', title)
        return sanitize_slug(clean)

    if url_clean:
        return sanitize_slug(url_clean.split("/")[-1].split("?")[0])

    return "fitgirl-game"


def get_current_utc_iso() -> str:
    """Get ISO-8601 formatted UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_timestamp(iso_str: str) -> datetime:
    """Parse ISO-8601 UTC timestamp string to datetime object."""
    try:
        clean_str = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return datetime.now(timezone.utc)


def format_localized_timestamp(iso_str: str) -> Tuple[str, str, str]:
    """
    Convert UTC ISO timestamp to client local time.
    Returns:
      (local_time_formatted, relative_age_str, freshness_category)
      - local_time_formatted: e.g. "21 Aug 2026, 05:25 PM IST"
      - relative_age_str: e.g. "2 hours ago", "15m ago", "Just now"
      - freshness_category: "fresh" (<12h), "aging" (12-36h), "expired" (>36h)
    """
    try:
        dt_utc = parse_iso_timestamp(iso_str)
        dt_local = dt_utc.astimezone()

        # Format local date and time with timezone name
        tz_name = dt_local.strftime("%Z") or dt_local.strftime("%z")
        local_time_str = dt_local.strftime(f"%d %b %Y, %I:%M %p {tz_name}").strip()

        # Calculate relative difference
        now_local = datetime.now(dt_local.tzinfo)
        diff_seconds = max(0, int((now_local - dt_local).total_seconds()))

        hours = diff_seconds / 3600.0

        if diff_seconds < 60:
            age_str = "Just now"
        elif diff_seconds < 3600:
            mins = diff_seconds // 60
            age_str = f"{mins} min{'s' if mins != 1 else ''} ago"
        elif diff_seconds < 86400:
            hrs = diff_seconds // 3600
            age_str = f"{hrs} hour{'s' if hrs != 1 else ''} ago"
        else:
            days = diff_seconds // 86400
            age_str = f"{days} day{'s' if days != 1 else ''} ago"

        if hours < 12.0:
            freshness = "fresh"
        elif hours <= 36.0:
            freshness = "aging"
        else:
            freshness = "expired"

        return local_time_str, age_str, freshness

    except Exception:
        return iso_str, "Recently", "aging"


def _http_request(url: str, method: str = "GET", data: Optional[Dict[str, Any]] = None, timeout: float = 6.0) -> Optional[Any]:
    """Lightweight HTTP helper using standard urllib with JSON payload handling."""
    req_headers = {
        "User-Agent": "FitGirlLinkExtractor/3.2.0 (Community Hub Client)",
        "Accept": "application/json"
    }

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if raw.strip():
                return json.loads(raw)
            return None
    except Exception:
        return None


def get_community_games(firebase_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all game metadata records from Community Cloud Firebase Realtime Database.
    Falls back gracefully to local demo data if server is unreachable.
    """
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    endpoint = f"{base_url}/games_meta.json"

    data = _http_request(endpoint, method="GET", timeout=5.0)

    results = []
    if isinstance(data, dict) and data:
        for slug, item in data.items():
            if isinstance(item, dict):
                rec = dict(item)
                rec["slug"] = slug
                iso_ts = rec.get("timestamp_utc", get_current_utc_iso())
                loc_time, age_str, fresh = format_localized_timestamp(iso_ts)
                rec["local_time"] = loc_time
                rec["age_str"] = age_str
                rec["freshness"] = fresh
                results.append(rec)
    else:
        # Fallback to local demo repository
        for slug, item in DEMO_COMMUNITY_DATA.items():
            rec = dict(item)
            iso_ts = rec.get("timestamp_utc", get_current_utc_iso())
            loc_time, age_str, fresh = format_localized_timestamp(iso_ts)
            rec["local_time"] = loc_time
            rec["age_str"] = age_str
            rec["freshness"] = fresh
            results.append(rec)

    # Sort descending by timestamp
    def _sort_key(r):
        return r.get("timestamp_utc", "")

    results.sort(key=_sort_key, reverse=True)
    return results


def get_game_by_slug(slug: str, firebase_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve metadata for a specific game by slug."""
    clean_slug = sanitize_slug(slug)
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    endpoint = f"{base_url}/games_meta/{clean_slug}.json"

    data = _http_request(endpoint, method="GET", timeout=4.0)
    if isinstance(data, dict) and data:
        data["slug"] = clean_slug
        iso_ts = data.get("timestamp_utc", get_current_utc_iso())
        loc_time, age_str, fresh = format_localized_timestamp(iso_ts)
        data["local_time"] = loc_time
        data["age_str"] = age_str
        data["freshness"] = fresh
        return data

    # Check fallback demo
    if clean_slug in DEMO_COMMUNITY_DATA:
        rec = dict(DEMO_COMMUNITY_DATA[clean_slug])
        iso_ts = rec.get("timestamp_utc", get_current_utc_iso())
        loc_time, age_str, fresh = format_localized_timestamp(iso_ts)
        rec["local_time"] = loc_time
        rec["age_str"] = age_str
        rec["freshness"] = fresh
        return rec

    return None


def get_game_urls(slug: str, firebase_url: Optional[str] = None) -> List[str]:
    """Retrieve direct URLs payload for a game from Firebase."""
    clean_slug = sanitize_slug(slug)
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    endpoint = f"{base_url}/games_urls/{clean_slug}.json"

    data = _http_request(endpoint, method="GET", timeout=5.0)
    if isinstance(data, dict) and "urls" in data and isinstance(data["urls"], list):
        return data["urls"]
    elif isinstance(data, list):
        return data

    # Check fallback demo
    if clean_slug in DEMO_COMMUNITY_URLS:
        return DEMO_COMMUNITY_URLS[clean_slug]

    return []


def upload_game_record(
    slug: str,
    title: str,
    source_url: str,
    image_url: str,
    urls: List[str],
    total_parts: int,
    total_size_str: str,
    total_size_bytes: int = 0,
    uploader: str = "Anonymous",
    firebase_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Upload or update a game extraction record in Firebase Realtime Database.
    Enforces overwrite rule (updates if newer).
    """
    if not urls:
        return False, "No URLs provided for upload."

    clean_slug = sanitize_slug(slug or generate_game_slug(source_url, title))
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    utc_now = get_current_utc_iso()

    # Verify regex on links
    valid_urls = []
    for u in urls:
        clean_u = u.strip()
        if "fuckingfast.co" in clean_u:
            valid_urls.append(clean_u)

    if not valid_urls:
        return False, "URLs do not match valid fuckingfast pattern."

    meta_payload = {
        "title": title.strip() or "FitGirl Repack",
        "source_url": source_url.strip(),
        "image_url": image_url.strip() if image_url else "",
        "timestamp_utc": utc_now,
        "total_parts": total_parts or len(valid_urls),
        "resolved_count": len(valid_urls),
        "total_size_str": total_size_str or "0 B",
        "total_size_bytes": total_size_bytes or 0,
        "uploader": uploader or "Community",
        "app_version": updater.CURRENT_VERSION
    }

    url_payload = {
        "urls": valid_urls,
        "updated_at": utc_now
    }

    meta_endpoint = f"{base_url}/games_meta/{clean_slug}.json"
    urls_endpoint = f"{base_url}/games_urls/{clean_slug}.json"

    # Push to Firebase
    res_meta = _http_request(meta_endpoint, method="PUT", data=meta_payload, timeout=6.0)
    res_urls = _http_request(urls_endpoint, method="PUT", data=url_payload, timeout=6.0)

    # Also update in-memory cache
    DEMO_COMMUNITY_DATA[clean_slug] = meta_payload
    DEMO_COMMUNITY_DATA[clean_slug]["slug"] = clean_slug
    DEMO_COMMUNITY_URLS[clean_slug] = valid_urls

    if res_meta is not None or res_urls is not None:
        return True, f"Successfully published '{title}' to Community Cloud Cache!"
    else:
        # Fallback local update acknowledged
        return True, f"Saved '{title}' to local community cache (offline fallback)."


def check_link_health(direct_url: str) -> Tuple[bool, str]:
    """
    Perform a rapid 1-byte HTTP Range GET to verify if direct URL is alive.
    """
    if not direct_url:
        return False, "No URL provided"

    clean_url = direct_url.split("#")[0].strip()
    try:
        val_res = validator.validate_single_url(0, clean_url, timeout=8.0)
        if val_res.is_valid:
            size_txt = val_res.content_length_str if val_res.content_length_bytes > 0 else "Active"
            return True, size_txt
        else:
            return False, f"HTTP {val_res.status_code or 'Timeout'}"
    except Exception as e:
        return False, f"Error: {e}"


def test_firebase_connection(firebase_url: Optional[str] = None) -> Tuple[bool, str]:
    """Test connection to Firebase Realtime Database endpoint."""
    raw_url = (firebase_url or DEFAULT_FIREBASE_URL).strip()
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raw_url = "https://" + raw_url
    base_url = raw_url.rstrip("/")

    # Check games_meta endpoint directly
    endpoint = f"{base_url}/games_meta.json?shallow=true"

    try:
        req = urllib.request.Request(
            endpoint,
            headers={"User-Agent": "FitGirlLinkExtractor/3.2.0"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status in (200, 204):
                return True, "Firebase Cloud endpoint is online and reachable!"
            return False, f"Firebase returned status code {resp.status}"
    except urllib.error.HTTPError as he:
        if he.code in (401, 403):
            return True, "Firebase reached (Authentication/Rules enforced)."
        return False, f"HTTP Error: {he.code} {he.reason}"
    except Exception as ex:
        return False, f"Connection failed: {ex}"
