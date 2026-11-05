"""Community Cloud Cache: the shared list of games and their direct links.

Everything read from the database is treated as untrusted and checked by links.py
and game_records.py. This module only ever adds or updates game records. It never
deletes them, because every client would then be able to remove other people's games.
"""

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import firebase_client
import game_records
import links
import utils
from firebase_client import FirebaseError
from version import APP_VERSION

log = logging.getLogger(__name__)

META_PATH = "games_meta"
URLS_PATH = "games_urls"
# Presence lives under one game's record because the database rules grew around that path.
PRESENCE_PATH = f"{META_PATH}/grand-theft-auto-v/presence"
PRESENCE_ACTIVE_SECONDS = 300
PRESENCE_PRUNE_LIMIT = 15

FEED_MAX_AGE_SECONDS = 300.0
FEED_TIMEOUT_SECONDS = 15.0

# Older versions saved these made-up records into the local cache file.
_LEGACY_DEMO_UPLOADERS = {"Community Scout", "CyberRunner", "KratosBlade"}

FeedCallback = Callable[[List[Dict[str, Any]]], None]


class _FeedState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.games: Optional[List[Dict[str, Any]]] = None
        self.synced_at = 0.0
        self.syncing = False
        self.offline = False
        self.waiting: List[FeedCallback] = []
        self.live_gamers = 1


_feed = _FeedState()


def reset_feed_cache() -> None:
    """Forget everything held in memory. The next read starts from the saved list."""
    global _feed
    _feed = _FeedState()


def _cache_file() -> str:
    return os.path.join(utils.get_app_data_dir(), "community_games_cache.json")


def _clean_feed(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    cleaned = (game_records.clean_feed_record(slug, record) for slug, record in raw.items())
    return game_records.dedupe_feed(record for record in cleaned if record)


def _load_cached_feed() -> List[Dict[str, Any]]:
    try:
        with open(_cache_file(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as error:
        log.warning("Ignoring unreadable community cache: %s", error)
        return []
    if not isinstance(data, list):
        return []
    usable = {
        record["slug"]: record
        for record in data
        if isinstance(record, dict)
        and isinstance(record.get("slug"), str)
        and record.get("uploader") not in _LEGACY_DEMO_UPLOADERS
    }
    return _clean_feed(usable)


def _save_cached_feed(games: List[Dict[str, Any]]) -> None:
    try:
        utils.write_json_atomic(_cache_file(), games)
    except OSError as error:
        log.warning("Could not save community cache: %s", error)


def _sync_feed(state: _FeedState) -> None:
    games: Optional[List[Dict[str, Any]]] = None
    try:
        games = _clean_feed(firebase_client.request(META_PATH, timeout=FEED_TIMEOUT_SECONDS))
    except FirebaseError as error:
        log.warning("Community feed sync failed: %s", error)
    except Exception:
        # A sync must always end below, or the feed would stay stuck as "syncing".
        log.exception("Could not process the community feed")

    with state.lock:
        if games is not None:
            state.games = games
        state.synced_at = time.time()
        state.offline = games is None
        state.syncing = False
        waiting, state.waiting = state.waiting, []
        current = list(state.games or [])

    if games is not None:
        _save_cached_feed(games)

    aged = [game_records.with_age(game) for game in current]
    for callback in waiting:
        try:
            callback(aged)
        except Exception:
            log.exception("Community feed listener failed")


def get_community_games(force_refresh: bool = False, on_synced: Optional[FeedCallback] = None) -> List[Dict[str, Any]]:
    """Return the games known right now, instantly, and refresh in the background if needed.

    on_synced is called when a background refresh ends, whether it worked or not. It
    is not called when the current list is recent enough to need no refresh.
    """
    state = _feed
    with state.lock:
        if state.games is None:
            state.games = _load_cached_feed()
        stale = time.time() - state.synced_at >= FEED_MAX_AGE_SECONDS
        start_sync = (force_refresh or stale) and not state.syncing
        if start_sync:
            state.syncing = True
        if state.syncing and on_synced and on_synced not in state.waiting:
            state.waiting.append(on_synced)
        games = list(state.games)

    if start_sync:
        threading.Thread(target=_sync_feed, args=(state,), daemon=True, name="feed-sync").start()
    return [game_records.with_age(game) for game in games]


def feed_status() -> Dict[str, bool]:
    """Whether the last sync failed and whether one is running now."""
    state = _feed
    with state.lock:
        return {"offline": state.offline, "syncing": state.syncing}


def get_game_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Read and validate one game's record directly from the database."""
    clean_slug = game_records.sanitize_slug(slug)
    try:
        raw = firebase_client.request(f"{META_PATH}/{clean_slug}", timeout=5.0)
    except FirebaseError as error:
        log.info("Could not read game %s: %s", clean_slug, error)
        return None
    record = game_records.clean_feed_record(clean_slug, raw)
    return game_records.with_age(record) if record else None


def get_game_urls(slug: str) -> List[str]:
    """The direct links for a game, or nothing at all if any of them cannot be trusted."""
    clean_slug = game_records.sanitize_slug(slug)
    try:
        data = firebase_client.request(f"{URLS_PATH}/{clean_slug}", timeout=8.0)
    except FirebaseError as error:
        log.warning("Could not read links for %s: %s", clean_slug, error)
        return []

    urls = data.get("urls") if isinstance(data, dict) else data
    if not isinstance(urls, list) or not urls:
        return []
    if not all(links.is_direct_link(url) for url in urls):
        log.warning("Rejected links for %s: a link is not on an allowed host", clean_slug)
        return []
    return urls


def upload_game_record(
    *,
    slug: str,
    title: str,
    source_url: str,
    image_url: str,
    urls: List[str],
    total_parts: int,
    total_size_str: str,
    total_size_bytes: int = 0,
) -> Tuple[bool, str]:
    """Publish one fully verified game. Returns (success, message)."""
    clean_urls = [url.strip() for url in urls if isinstance(url, str) and url.strip()]
    if not clean_urls:
        return False, "No links to publish."
    if not all(links.is_direct_link(url) for url in clean_urls):
        return False, "Refused to publish a link that is not on an allowed host."

    clean_slug = game_records.sanitize_slug(slug or game_records.generate_game_slug(source_url, title))
    now = game_records.utc_now_iso()
    # PATCH leaves used_count and the presence data on a record untouched.
    meta = {
        "title": title.strip() or "FitGirl Repack",
        "source_url": source_url.strip() if links.is_allowed_source_url(source_url.strip()) else "",
        "image_url": image_url if links.is_safe_image_url(image_url) else "",
        "timestamp_utc": now,
        "total_parts": total_parts or len(clean_urls),
        "resolved_count": len(clean_urls),
        "total_size_str": total_size_str or "0 B",
        "total_size_bytes": total_size_bytes or 0,
        "uploader": "Community",
        "app_version": APP_VERSION,
    }

    try:
        # Links first, so the feed never lists a game whose links are not there yet.
        firebase_client.request(f"{URLS_PATH}/{clean_slug}", "PUT", {"urls": clean_urls, "updated_at": now})
        firebase_client.request(f"{META_PATH}/{clean_slug}", "PATCH", meta)
    except FirebaseError as error:
        log.warning("Could not publish %s: %s", clean_slug, error)
        return False, f"Could not publish to the community: {error}"

    _add_to_feed(clean_slug, meta)
    return True, f"Published '{meta['title']}' to the community."


def _add_to_feed(slug: str, meta: Dict[str, Any]) -> None:
    record = game_records.clean_feed_record(slug, meta)
    if record is None:
        return
    state = _feed
    with state.lock:
        known = next((game for game in state.games or [] if game.get("slug") == slug), None)
        if known:
            record["used_count"] = known.get("used_count", 0)
        others = [game for game in state.games or [] if game.get("slug") != slug]
        state.games = game_records.dedupe_feed([record, *others])
        games = list(state.games)
    _save_cached_feed(games)


def _parse_local_timestamp(value: str) -> str:
    """Convert a history timestamp in local time to the UTC form used everywhere else."""
    try:
        local = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").astimezone()
    except (TypeError, ValueError):
        return ""
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _match_in_community(query: str) -> Optional[Dict[str, Any]]:
    match = game_records.find_match(query, get_community_games())
    if match or "://" not in query:
        return match or get_game_by_slug(query)
    if links.is_fitgirl_page_url(query):
        return get_game_by_slug(game_records.generate_game_slug(query))
    return None


def _match_in_history(query: str, history_records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    complete = [
        {**row, "slug": game_records.generate_game_slug(row.get("source_url") or "", row.get("title") or "")}
        for row in history_records
        if (row.get("resolved_count") or 0) >= (row.get("total_parts") or 0) and row.get("urls")
    ]
    return game_records.find_match(query, complete)


def find_existing_game(query: str, history_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Look for exactly this game in the community cache, then in local history."""
    clean = (query or "").strip()
    if not clean:
        return {"exists": False}

    game = _match_in_community(clean)
    if game:
        urls = get_game_urls(game["slug"])
        if urls:
            expired = game.get("freshness") == "expired"
            return {
                "exists": True,
                "source": "community",
                "is_expired": expired,
                "record": {**game, "is_expired": expired, "source": "community", "urls": urls},
            }

    row = _match_in_history(clean, history_records)
    if row:
        timestamp = _parse_local_timestamp(row.get("timestamp", ""))
        age = game_records.describe_age(timestamp)
        expired = age.freshness == "expired"
        return {
            "exists": True,
            "source": "history",
            "is_expired": expired,
            "record": {
                "slug": row["slug"],
                "title": row.get("title", "FitGirl Repack"),
                "image_url": "",
                "source_url": row.get("source_url", clean),
                "total_parts": row.get("total_parts", len(row["urls"])),
                "total_size_str": row.get("total_size_str", "0 B"),
                "age_str": age.age_str,
                "timestamp_utc": timestamp,
                "freshness": age.freshness,
                "is_expired": expired,
                "used_count": 0,
                "source": "history",
                "urls": row["urls"],
            },
        }
    return {"exists": False}


def _is_recent(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    timestamp = entry.get("t")
    if not isinstance(timestamp, str):
        return False
    try:
        seen = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return abs((datetime.now(timezone.utc) - seen).total_seconds()) <= PRESENCE_ACTIVE_SECONDS
    except (TypeError, ValueError):
        return False


def ping_presence(session_id: str) -> int:
    """Renew this session's heartbeat and return how many sessions are active."""
    state = _feed
    session = re.sub(r"[^a-zA-Z0-9_-]", "", session_id or "")[:32]
    try:
        if session:
            firebase_client.request(
                f"{PRESENCE_PATH}/{session}", "PUT", {"t": game_records.utc_now_iso(), "v": APP_VERSION}, timeout=4.0
            )
        sessions = firebase_client.request(PRESENCE_PATH, timeout=4.0)
    except FirebaseError as error:
        log.debug("Presence update failed: %s", error)
        return state.live_gamers

    if not isinstance(sessions, dict):
        return state.live_gamers

    stale = [key for key, entry in sessions.items() if not _is_recent(entry)]
    state.live_gamers = max(1, len(sessions) - len(stale))
    if stale:
        threading.Thread(target=_prune_presence, args=(stale,), daemon=True, name="presence-prune").start()
    return state.live_gamers


def _prune_presence(keys: List[str]) -> None:
    for key in keys[:PRESENCE_PRUNE_LIMIT]:
        safe = firebase_client.safe_key(key)
        if not safe:
            continue
        try:
            firebase_client.request(f"{PRESENCE_PATH}/{safe}", "DELETE", timeout=3.0)
        except FirebaseError as error:
            log.debug("Presence prune failed: %s", error)
            return


def increment_game_usage(slug: str) -> int:
    """Count one grab of a game already in the database. Returns the new count, or 0 if none."""
    clean_slug = game_records.sanitize_slug(slug)
    try:
        exists = firebase_client.request(
            f"{META_PATH}/{clean_slug}", query={"shallow": "true"}, timeout=4.0
        )
        if not exists:
            return 0
        count = firebase_client.request(
            f"{META_PATH}/{clean_slug}/used_count", "PUT", {".sv": {"increment": 1}}, timeout=4.0
        )
    except FirebaseError as error:
        log.info("Could not count a grab for %s: %s", clean_slug, error)
        return 0
    return count if isinstance(count, int) else 0


def get_community_stats() -> Dict[str, int]:
    """Live count and total grabs from what is already known. Never touches the network."""
    state = _feed
    with state.lock:
        if state.games is None:
            state.games = _load_cached_feed()
        grabs = sum(int(game.get("used_count") or 0) for game in state.games)
        return {"live_gamers": state.live_gamers, "total_grabs": grabs}
