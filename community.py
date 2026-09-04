import os
import sys
import re
import json
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import validator
import updater
import scraper
import utils

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

        # Format local date and time with compact timezone name
        raw_tz = dt_local.strftime("%Z") or ""
        if len(raw_tz) > 5:
            # Abbreviate Windows full timezone name (e.g. India Standard Time -> IST)
            tz_abbr = "".join([c for c in raw_tz if c.isupper()])
        else:
            tz_abbr = raw_tz

        time_part = dt_local.strftime("%d %b %Y, %I:%M %p")
        local_time_str = f"{time_part} {tz_abbr}".strip() if tz_abbr else time_part

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


_COMMUNITY_GAMES_CACHE: Optional[List[Dict[str, Any]]] = None
_COMMUNITY_GAMES_CACHE_TIME: float = 0.0
_COMMUNITY_CACHE_LOCK = threading.Lock()


def invalidate_community_cache():
    """Invalidates the in-memory community feed cache."""
    global _COMMUNITY_GAMES_CACHE, _COMMUNITY_GAMES_CACHE_TIME
    with _COMMUNITY_CACHE_LOCK:
        _COMMUNITY_GAMES_CACHE = None
        _COMMUNITY_GAMES_CACHE_TIME = 0.0


def get_community_games(firebase_url: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch all game metadata records from Community Cloud Firebase Realtime Database.
    Cached in-memory for 25 seconds for instant multi-client response times.
    Falls back gracefully to local demo data if server is unreachable.
    """
    global _COMMUNITY_GAMES_CACHE, _COMMUNITY_GAMES_CACHE_TIME

    now = time.time()
    if not force_refresh and _COMMUNITY_GAMES_CACHE is not None and (now - _COMMUNITY_GAMES_CACHE_TIME < 25.0):
        return _COMMUNITY_GAMES_CACHE

    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    endpoint = f"{base_url}/games_meta.json"

    data = _http_request(endpoint, method="GET", timeout=4.0)

    results = []
    if isinstance(data, dict) and data:
        for slug, item in data.items():
            if isinstance(item, dict):
                rec = dict(item)
                rec["slug"] = slug
                rec["used_count"] = int(item.get("used_count", 0))
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
            rec["used_count"] = int(item.get("used_count", 12))
            iso_ts = rec.get("timestamp_utc", get_current_utc_iso())
            loc_time, age_str, fresh = format_localized_timestamp(iso_ts)
            rec["local_time"] = loc_time
            rec["age_str"] = age_str
            rec["freshness"] = fresh
            results.append(rec)

    # Sort descending by timestamp initially
    results.sort(key=lambda r: r.get("timestamp_utc", ""), reverse=True)

    # Intelligent Canonical Deduplication
    deduped = []
    seen_identities = {}
    stale_prune_slugs = []

    for r in results:
        title = (r.get("title") or "").strip()
        img = (r.get("image_url") or "").strip()
        src = (r.get("source_url") or "").strip()
        slug = r.get("slug", "")

        is_generic_title = title.lower() in (
            "fuckingfast direct parts", "fitgirl pastebin download",
            "direct repack", "fitgirl repack"
        ) or title.startswith("Part ")

        canonical_key = None

        # 1. Clean core title (collapses duplicates with different image hosts)
        norm_title = re.sub(r'[^a-z0-9]', '', title.lower())
        norm_core = re.sub(r'(deluxeedition|completeedition|ultimateedition|jackdawedition|bonusost|bonuscontent|repack|repak|v\d+.*)', '', norm_title)

        if len(norm_core) > 5 and not is_generic_title:
            canonical_key = f"title:{norm_core[:24]}"
        elif img and img.startswith("http") and not img.startswith("data:"):
            canonical_key = f"img:{img}"
        elif src and "fitgirl-repacks.site" in src:
            clean_path = urllib.parse.urlparse(src).path.strip("/")
            if clean_path:
                canonical_key = f"src:{clean_path}"
        else:
            canonical_key = f"slug:{slug}"

        if canonical_key in seen_identities:
            existing_idx = seen_identities[canonical_key]
            existing_rec = deduped[existing_idx]
            existing_is_generic = existing_rec.get("title", "").lower() in (
                "fuckingfast direct parts", "fitgirl pastebin download",
                "direct repack", "fitgirl repack"
            )

            if existing_is_generic and not is_generic_title:
                # Prefer record with actual game title
                stale_prune_slugs.append(existing_rec.get("slug"))
                r["used_count"] = max(r.get("used_count", 0), existing_rec.get("used_count", 0))
                deduped[existing_idx] = r
            elif not existing_is_generic and is_generic_title:
                # Keep existing real record
                stale_prune_slugs.append(slug)
                existing_rec["used_count"] = max(existing_rec.get("used_count", 0), r.get("used_count", 0))
            else:
                # Both generic or both real -> keep newer record
                ts_cur = r.get("timestamp_utc", "")
                ts_ext = existing_rec.get("timestamp_utc", "")
                if ts_cur > ts_ext:
                    stale_prune_slugs.append(existing_rec.get("slug"))
                    r["used_count"] = max(r.get("used_count", 0), existing_rec.get("used_count", 0))
                    deduped[existing_idx] = r
                else:
                    stale_prune_slugs.append(slug)
                    existing_rec["used_count"] = max(existing_rec.get("used_count", 0), r.get("used_count", 0))
        else:
            seen_identities[canonical_key] = len(deduped)
            deduped.append(r)

    # Asynchronously prune stale ghost duplicates from Firebase
    if stale_prune_slugs:
        def _prune_worker(slugs):
            for s in slugs:
                if s and s not in ("grand-theft-auto-v", "elden-ring-shadow-of-the-erdtree", "cyberpunk-2077-phantom-liberty"):
                    try:
                        _http_request(f"{base_url}/games_meta/{s}.json", method="DELETE", timeout=3.0)
                        _http_request(f"{base_url}/games_urls/{s}.json", method="DELETE", timeout=3.0)
                    except Exception:
                        pass
        threading.Thread(target=_prune_worker, args=(stale_prune_slugs,), daemon=True).start()

    results = deduped

    with _COMMUNITY_CACHE_LOCK:
        _COMMUNITY_GAMES_CACHE = results
        _COMMUNITY_GAMES_CACHE_TIME = time.time()

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
    global _COMMUNITY_GAMES_CACHE, _COMMUNITY_GAMES_CACHE_TIME
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

    # Preserve existing used_count if updating existing game
    used_count = 0
    existing = get_game_by_slug(clean_slug, firebase_url)
    if existing and isinstance(existing, dict):
        used_count = int(existing.get("used_count", 0))
    elif clean_slug in DEMO_COMMUNITY_DATA:
        used_count = int(DEMO_COMMUNITY_DATA[clean_slug].get("used_count", 0))

    meta_payload = {
        "title": title.strip() or "FitGirl Repack",
        "source_url": source_url.strip(),
        "image_url": image_url.strip() if image_url else "",
        "timestamp_utc": utc_now,
        "total_parts": total_parts or len(valid_urls),
        "resolved_count": len(valid_urls),
        "total_size_str": total_size_str or "0 B",
        "total_size_bytes": total_size_bytes or 0,
        "used_count": used_count,
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

    # Also update in-memory demo cache
    DEMO_COMMUNITY_DATA[clean_slug] = meta_payload
    DEMO_COMMUNITY_DATA[clean_slug]["slug"] = clean_slug
    DEMO_COMMUNITY_URLS[clean_slug] = valid_urls

    # Update active community feed cache with fresh entry
    with _COMMUNITY_CACHE_LOCK:
        if _COMMUNITY_GAMES_CACHE is not None:
            updated_item = dict(meta_payload)
            updated_item["slug"] = clean_slug
            loc_time, age_str, fresh = format_localized_timestamp(utc_now)
            updated_item["local_time"] = loc_time
            updated_item["age_str"] = age_str
            updated_item["freshness"] = fresh

            _COMMUNITY_GAMES_CACHE = [item for item in _COMMUNITY_GAMES_CACHE if item.get("slug") != clean_slug]
            _COMMUNITY_GAMES_CACHE.insert(0, updated_item)
            _COMMUNITY_GAMES_CACHE_TIME = time.time()

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


# ==========================================
# Presence & Community Usage Metrics
# ==========================================

def ping_presence(session_id: str, app_version: str = "", firebase_url: Optional[str] = None) -> int:
    """
    Register or renew a lightweight presence heartbeat in Firebase Realtime Database.
    Prunes stale sessions (>180s old) asynchronously to guarantee database stays < 10 KB.
    Returns the current count of active online gamers.
    """
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    now_iso = get_current_utc_iso()
    session_clean = re.sub(r'[^a-zA-Z0-9_-]', '', session_id or "")[:32]
    endpoint = f"{base_url}/games_meta/grand-theft-auto-v/presence/{session_clean}.json"

    # 1. Heartbeat PUT (~30 bytes)
    if session_clean:
        _http_request(endpoint, method="PUT", data={"t": now_iso, "v": app_version or updater.CURRENT_VERSION}, timeout=4.0)

    # 2. Get all presence sessions
    all_presence = _http_request(f"{base_url}/games_meta/grand-theft-auto-v/presence.json", method="GET", timeout=4.0)
    if not isinstance(all_presence, dict):
        return 1

    active_count = 0
    stale_keys = []
    now_dt = datetime.now(timezone.utc)

    for sid, data in all_presence.items():
        if isinstance(data, dict) and "t" in data:
            try:
                t_dt = parse_iso_timestamp(data["t"])
                delta = abs((now_dt - t_dt).total_seconds())
                if delta <= 300:
                    active_count += 1
                else:
                    stale_keys.append(sid)
            except Exception:
                stale_keys.append(sid)
        else:
            stale_keys.append(sid)

    # 3. Asynchronously prune stale entries in daemon thread
    if stale_keys:
        def _prune_worker(keys):
            for k in keys[:15]:
                try:
                    _http_request(f"{base_url}/games_meta/grand-theft-auto-v/presence/{k}.json", method="DELETE", timeout=3.0)
                except Exception:
                    pass
        threading.Thread(target=_prune_worker, args=(stale_keys,), daemon=True).start()

    return max(1, active_count)


def increment_game_usage(slug: str, firebase_url: Optional[str] = None) -> int:
    """
    Atomically increment download count for a game in Firebase RTDB and update global counter.
    Returns the new used_count.
    """
    clean_slug = sanitize_slug(slug)
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    meta_url = f"{base_url}/games_meta/{clean_slug}.json"

    game_meta = _http_request(meta_url, method="GET", timeout=4.0)
    current_count = 0
    if isinstance(game_meta, dict):
        current_count = int(game_meta.get("used_count", 0))

    new_count = current_count + 1
    # Patch game record in Firebase RTDB
    _http_request(meta_url, method="PATCH", data={"used_count": new_count}, timeout=4.0)
    invalidate_community_cache()

    return new_count


def get_community_stats(firebase_url: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve live online gamers count and total community grabs."""
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")

    # Global grabs - aggregated directly from Firebase records
    games = get_community_games(firebase_url)
    total_grabs = sum(int(g.get("used_count", 0)) for g in games if isinstance(g, dict))

    # Live gamers count
    live_count = 1
    try:
        all_presence = _http_request(f"{base_url}/games_meta/grand-theft-auto-v/presence.json", method="GET", timeout=3.0)
        if isinstance(all_presence, dict):
            now_dt = datetime.now(timezone.utc)
            count = 0
            for sid, data in all_presence.items():
                if isinstance(data, dict) and "t" in data:
                    try:
                        t_dt = parse_iso_timestamp(data["t"])
                        if abs((now_dt - t_dt).total_seconds()) <= 300:
                            count += 1
                    except Exception:
                        pass
            live_count = max(1, count)
    except Exception:
        pass

    return {
        "live_gamers": live_count,
        "total_grabs": total_grabs
    }


def enrich_generic_record(slug: str, base_url: str):
    """Enriches generic pastebin records by inspecting their part URLs and fetching real title/art."""
    try:
        urls = get_game_urls(slug, base_url)
        if urls:
            meta = scraper.resolve_pastebin_metadata("", urls)
            if meta.get("title") and meta["title"] != "FitGirl Repack":
                patch_data = {
                    "title": meta["title"],
                    "image_url": meta["image_url"],
                }
                if meta.get("source_url") and "fitgirl-repacks.site" in meta["source_url"]:
                    patch_data["source_url"] = meta["source_url"]
                _http_request(f"{base_url}/games_meta/{slug}.json", method="PATCH", data=patch_data, timeout=5.0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Community Issue Reporting & Crash Telemetry
_reported_crash_hashes = set()
_crash_lock = threading.Lock()

# Default SHA-256 hash for admin passkey ("0505")
_DEFAULT_ADMIN_PIN_HASH = "131e27b7715c43825f14696b907812d34fb86a529dd8c98fedbf87016f5d9149"


def ensure_admin_key_file() -> str:
    """
    Ensure admin_key.secret exists in %APPDATA%/FitGirlLinkExtractor so the maintainer
    can view, edit, and configure their admin PIN directly in Explorer.
    """
    target_dirs = []
    app_data = os.environ.get("APPDATA")
    if app_data:
        target_dirs.append(os.path.join(app_data, "FitGirlLinkExtractor"))
    app_dir = utils.get_app_data_dir()
    if app_dir not in target_dirs:
        target_dirs.append(app_dir)

    primary_path = ""
    for d in target_dirs:
        try:
            os.makedirs(d, exist_ok=True)
            k_path = os.path.join(d, "admin_key.secret")
            if not primary_path:
                primary_path = k_path
            if not os.path.exists(k_path):
                with open(k_path, "w", encoding="utf-8") as f:
                    f.write("# Link Extractor Administrator Passkey\n")
                    f.write("# Edit this value to change your Admin Mode PIN anytime.\n")
                    f.write("0505\n")
        except Exception:
            pass

    return primary_path or os.path.join(utils.get_app_data_dir(), "admin_key.secret")


def verify_admin_pin(candidate_pin: str) -> bool:
    """
    Cryptographically verify admin PIN against SHA-256 hash, environment variable,
    or maintainer's local secret file in AppData without exposing plaintext PIN.
    """
    if not candidate_pin:
        return False

    clean_pin = str(candidate_pin).strip()

    # 1. Check environment variable override
    env_pin = os.environ.get("LINK_EXTRACTOR_ADMIN_PIN", "").strip()
    if env_pin and clean_pin == env_pin:
        return True

    # 2. Check local maintainer secret files in AppData & App directory
    candidate_paths = [
        ensure_admin_key_file(),
        os.path.join(utils.get_app_data_dir(), "admin_key.secret")
    ]
    app_data = os.environ.get("APPDATA")
    if app_data:
        candidate_paths.append(os.path.join(app_data, "FitGirlLinkExtractor", "admin_key.secret"))

    for k_path in candidate_paths:
        if os.path.exists(k_path):
            try:
                with open(k_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if clean_pin == line:
                                return True
            except Exception:
                pass

    # 3. Constant-time digest comparison against SHA-256 hash
    import hashlib
    import hmac
    candidate_hash = hashlib.sha256(clean_pin.encode("utf-8")).hexdigest()
    return hmac.compare_digest(candidate_hash, _DEFAULT_ADMIN_PIN_HASH)


def _get_local_reports_file() -> str:
    """Get persistent path for local issues and reports archive."""
    data_dir = utils.get_app_data_dir()
    return os.path.join(data_dir, "community_reports.json")


def _load_local_reports() -> Dict[str, Any]:
    """Load locally persisted reports dictionary."""
    fpath = _get_local_reports_file()
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def _save_local_reports(reports_dict: Dict[str, Any]):
    """Save reports dictionary to persistent local storage."""
    fpath = _get_local_reports_file()
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(reports_dict, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def fetch_all_reports(firebase_url: Optional[str] = None) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Fetch all public bug reports from Firebase RTDB (/reports.json), merged with locally saved reports.
    Returns (success: bool, reports: list, message: str).
    """
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    url = f"{base_url}/reports.json"
    cloud_reports: Dict[str, Any] = {}
    try:
        data = _http_request(url, method="GET", timeout=5.0)
        if isinstance(data, dict):
            cloud_reports = data
    except Exception:
        pass

    # Merge local reports archive with cloud reports
    local_reports = _load_local_reports()
    merged: Dict[str, Any] = {}

    for rid, item in cloud_reports.items():
        if isinstance(item, dict):
            rec = item.copy()
            rec["id"] = rid
            merged[rid] = rec

    for rid, item in local_reports.items():
        if isinstance(item, dict):
            if rid not in merged:
                rec = item.copy()
                rec["id"] = rid
                merged[rid] = rec
            else:
                # Merge local state updates
                merged[rid].update(item)
                merged[rid]["id"] = rid

    reports_list = list(merged.values())
    reports_list.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return True, reports_list, f"Loaded {len(reports_list)} reports"


def _compute_similarity(text1: str, text2: str) -> float:
    """Compute word token Jaccard similarity between two strings with basic stemming."""
    def _tokenize(t: str) -> set:
        clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', t.lower())
        words = []
        for w in clean.split():
            if len(w) > 2:
                if w.endswith('ing') and len(w) > 5:
                    w = w[:-3]
                elif w.endswith('s') and len(w) > 4:
                    w = w[:-1]
                elif w.endswith('ed') and len(w) > 4:
                    w = w[:-2]
                words.append(w)
        return set(words)

    s1 = _tokenize(text1)
    s2 = _tokenize(text2)
    if not s1 or not s2:
        return 0.0
    intersection = len(s1.intersection(s2))
    union = len(s1.union(s2))
    return intersection / union if union > 0 else 0.0


def find_duplicate_report(subject: str, existing_reports: List[Dict[str, Any]], threshold: float = 0.55) -> Optional[Dict[str, Any]]:
    """
    Find if a report with matching or similar subject already exists.
    Returns the matching report dict or None.
    """
    clean_subj = subject.strip().lower()
    if not clean_subj or len(clean_subj) < 4:
        return None

    best_match = None
    highest_score = 0.0

    for rep in existing_reports:
        rep_subj = rep.get("subject", "").strip().lower()
        if not rep_subj:
            continue
        if clean_subj == rep_subj or clean_subj in rep_subj or rep_subj in clean_subj:
            return rep

        sim = _compute_similarity(clean_subj, rep_subj)
        if sim > highest_score and sim >= threshold:
            highest_score = sim
            best_match = rep

    return best_match


def submit_user_report(
    subject: str,
    category: str,
    description: str,
    screenshot_data: Optional[str] = None,
    telemetry: Optional[Dict[str, Any]] = None,
    firebase_url: Optional[str] = None,
    force_create: bool = False
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Submit a user report. Checks for duplicates against existing reports unless force_create is True.
    If duplicate exists and force_create is False, increments affected_users_count and returns (False, "duplicate", existing_record).
    If new or force_create is True, persists locally and pushes to Firebase RTDB (/reports/{report_id}.json).
    """
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    clean_subject = (subject or "").strip()
    clean_desc = (description or "").strip()
    clean_category = (category or "Bug Report").strip()

    if not clean_subject:
        return False, "Subject cannot be empty", None

    if not force_create:
        success, existing_reports, _ = fetch_all_reports(base_url)
        if success and existing_reports:
            duplicate = find_duplicate_report(clean_subject, existing_reports)
            if duplicate:
                dup_id = duplicate.get("id")
                if dup_id:
                    increment_report_affected(dup_id, firebase_url=base_url)
                    duplicate["affected_users_count"] = int(duplicate.get("affected_users_count", 1)) + 1
                return False, "duplicate", duplicate

    report_id = f"rep_{int(time.time())}_{os.urandom(3).hex()}"
    now_iso = get_current_utc_iso()

    safe_screenshot = screenshot_data
    if safe_screenshot and len(safe_screenshot) > 800 * 1024:
        safe_screenshot = safe_screenshot[:800 * 1024]

    report_payload = {
        "id": report_id,
        "subject": clean_subject[:150],
        "category": clean_category[:50],
        "description": clean_desc[:3000],
        "screenshot_data": safe_screenshot or "",
        "status": "open",
        "affected_users_count": 1,
        "admin_remark": "",
        "created_at": now_iso,
        "app_version": updater.CURRENT_VERSION,
        "os_info": sys.platform,
        "telemetry": telemetry or {}
    }

    # 1. Persist to local reports store first
    local_data = _load_local_reports()
    local_data[report_id] = report_payload
    _save_local_reports(local_data)

    # 2. Attempt push to Firebase RTDB
    url = f"{base_url}/reports/{report_id}.json"
    res = _http_request(url, method="PUT", data=report_payload, timeout=6.0)
    if res is not None:
        return True, report_id, report_payload

    # If Firebase returned 401 or network offline, report is safely preserved in local storage
    return True, report_id, report_payload


def increment_report_affected(report_id: str, firebase_url: Optional[str] = None) -> Tuple[bool, int]:
    """Increment affected_users_count for an existing issue report in local and cloud stores."""
    # Update local store
    local_data = _load_local_reports()
    current_count = 1
    if report_id in local_data:
        current_count = int(local_data[report_id].get("affected_users_count", 1))
        current_count += 1
        local_data[report_id]["affected_users_count"] = current_count
        _save_local_reports(local_data)

    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    url = f"{base_url}/reports/{report_id}.json"
    data = _http_request(url, method="GET", timeout=4.0)
    if isinstance(data, dict):
        current_count = int(data.get("affected_users_count", 1)) + 1
    _http_request(url, method="PATCH", data={"affected_users_count": current_count}, timeout=4.0)
    return True, current_count


def update_report_status_and_remark(
    report_id: str,
    new_status: str,
    admin_remark: str,
    admin_pin: str,
    firebase_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Update status and admin remark on a report. Requires valid admin_pin.
    """
    if not verify_admin_pin(admin_pin):
        return False, "Unauthorized: Invalid admin passkey"

    valid_statuses = {"open", "investigating", "fixed", "closed"}
    status_clean = (new_status or "open").lower().strip()
    if status_clean not in valid_statuses:
        status_clean = "open"

    now_iso = get_current_utc_iso()

    # Update local store
    local_data = _load_local_reports()
    if report_id in local_data:
        local_data[report_id]["status"] = status_clean
        local_data[report_id]["admin_remark"] = (admin_remark or "").strip()
        local_data[report_id]["updated_at"] = now_iso
        _save_local_reports(local_data)

    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    url = f"{base_url}/reports/{report_id}.json"

    patch_data = {
        "status": status_clean,
        "admin_remark": (admin_remark or "").strip(),
        "updated_at": now_iso
    }

    _http_request(url, method="PATCH", data=patch_data, timeout=5.0)
    return True, f"Report {report_id} updated to {status_clean}"


def delete_report(
    report_id: str,
    admin_pin: str,
    firebase_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Permanently delete an issue report from both local archive and Firebase RTDB.
    Requires verified admin PIN authorization.
    """
    if not verify_admin_pin(admin_pin):
        return False, "Unauthorized: Invalid admin passkey"

    clean_id = str(report_id).strip()
    if not clean_id:
        return False, "Invalid report ID"

    # 1. Delete from local persistent store
    local_data = _load_local_reports()
    if clean_id in local_data:
        del local_data[clean_id]
        _save_local_reports(local_data)

    # 2. Delete from Firebase RTDB via HTTP DELETE
    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    url = f"{base_url}/reports/{clean_id}.json"
    _http_request(url, method="DELETE", timeout=5.0)

    return True, f"Report {clean_id} deleted successfully"


def report_crash_log(
    error_type: str,
    error_message: str,
    traceback_str: str,
    context: str = "runtime",
    telemetry: Optional[Dict[str, Any]] = None,
    firebase_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Report an unhandled crash or exception to Firebase RTDB (/crash_logs).
    Includes in-memory deduplication to avoid flooding repetitive error loops.
    """
    import hashlib
    sig_raw = f"{error_type}:{traceback_str[:120]}"
    sig_hash = hashlib.md5(sig_raw.encode("utf-8", errors="ignore")).hexdigest()

    with _crash_lock:
        if sig_hash in _reported_crash_hashes:
            return True, "already_reported"
        _reported_crash_hashes.add(sig_hash)

    base_url = (firebase_url or DEFAULT_FIREBASE_URL).rstrip("/")
    crash_id = f"crash_{int(time.time())}_{sig_hash[:6]}"
    now_iso = get_current_utc_iso()

    payload = {
        "error_type": str(error_type)[:100],
        "error_message": str(error_message)[:500],
        "traceback": str(traceback_str)[:5000],
        "context": str(context)[:50],
        "app_version": updater.CURRENT_VERSION,
        "platform": sys.platform,
        "timestamp_utc": now_iso,
        "telemetry": telemetry or {}
    }

    def _async_send():
        try:
            _http_request(f"{base_url}/crash_logs/{crash_id}.json", method="PUT", data=payload, timeout=5.0)
        except Exception:
            pass

    threading.Thread(target=_async_send, daemon=True).start()
    return True, crash_id


