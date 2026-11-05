"""Rules about game records: identity, freshness, and which shared data can be trusted.

Everything here is pure and works on plain dictionaries. There is one definition of
"the same game" and one definition of "expired", used by the feed and every lookup.
"""

import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

import links

FRESH_HOURS = 12.0
EXPIRED_HOURS = 24.0
_FUTURE_TOLERANCE_SECONDS = 300

GENERIC_TITLES = {
    "direct repack",
    "fitgirl repack",
    "fitgirl repack download",
    "fitgirl pastebin repack",
    "fitgirl pastebin download",
    "fuckingfast direct parts",
}

_MAX_TITLE_LENGTH = 300
_TEXT_FIELDS = ("source_url", "timestamp_utc", "total_size_str", "uploader", "app_version")
_NUMBER_FIELDS = ("total_parts", "resolved_count", "total_size_bytes", "used_count")

# Cut a trailing version such as "- v1.2.3 + 5 DLCs" so updates of one game count as the same game.
_VERSION_TAIL = re.compile(r"[\s\-–—:,]*\bv\.?\d[\w.\-]*.*$", re.IGNORECASE)
_BONUS_TAIL = re.compile(r"\s\+\s(?:\d+|all|bonus|dlc).*$", re.IGNORECASE)


@dataclass(frozen=True)
class Age:
    local_time: str
    age_str: str
    freshness: str  # "fresh" | "aging" | "expired"


def sanitize_slug(text: str) -> str:
    """Turn any text into a single safe database key."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", (text or "").lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "unnamed-game"


def generate_game_slug(url: str, title: str = "") -> str:
    """The canonical key for a game: its FitGirl page if it has one, otherwise its title."""
    clean_url = (url or "").strip()
    if links.is_fitgirl_page_url(clean_url):
        return _page_slug(clean_url)
    if title:
        return sanitize_slug(re.sub(r"\[.*?\]|\(.*?\)", "", title))
    if clean_url:
        return sanitize_slug(clean_url.split("/")[-1].split("?")[0])
    return "fitgirl-game"


def _page_slug(url: str) -> str:
    segments = [segment for segment in urllib.parse.urlparse(url).path.split("/") if segment]
    return sanitize_slug(segments[-1])


def is_generic_title(title: str) -> bool:
    """Placeholder titles that say nothing about which game a record holds."""
    clean = (title or "").strip().lower()
    return not clean or clean in GENERIC_TITLES or clean.startswith("part ")


def normalize_title(title: str) -> str:
    """A title reduced to letters and digits, without a trailing version number."""
    text = _VERSION_TAIL.sub("", (title or "")[:_MAX_TITLE_LENGTH])
    text = _BONUS_TAIL.sub("", text)
    return re.sub(r"[^a-z0-9]", "", text.lower())


def utc_now_iso() -> str:
    """The current time in the UTC format stored in the database."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value: str) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def describe_age(timestamp_utc: str) -> Age:
    """Local time, relative age and freshness of a UTC timestamp.

    Unreadable or far-future timestamps count as expired, so a bad record can
    never present itself as fresh.
    """
    parsed = _parse_timestamp(timestamp_utc)
    if parsed is None:
        return Age("", "Unknown age", "expired")

    seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    if seconds < -_FUTURE_TOLERANCE_SECONDS:
        return Age("", "Unknown age", "expired")
    seconds = max(0, int(seconds))

    local = parsed.astimezone()
    zone = local.strftime("%Z") or ""
    if len(zone) > 5:  # Windows gives full names such as "India Standard Time".
        zone = "".join(char for char in zone if char.isupper())
    local_time = f"{local.strftime('%d %b %Y, %I:%M %p')} {zone}".strip()

    hours = seconds / 3600.0
    if hours < FRESH_HOURS:
        freshness = "fresh"
    elif hours < EXPIRED_HOURS:
        freshness = "aging"
    else:
        freshness = "expired"
    return Age(local_time, _relative_age(seconds), freshness)


def _relative_age(seconds: int) -> str:
    if seconds < 60:
        return "Just now"
    for size, unit in ((86400, "day"), (3600, "hour"), (60, "min")):
        if seconds >= size:
            count = seconds // size
            return f"{count} {unit}{'s' if count != 1 else ''} ago"
    return "Just now"


def with_age(record: Dict[str, Any]) -> Dict[str, Any]:
    """A copy of a record with its age fields calculated for right now."""
    age = describe_age(record.get("timestamp_utc", ""))
    return {**record, "local_time": age.local_time, "age_str": age.age_str, "freshness": age.freshness}


def _number(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return 0


def clean_feed_record(slug: str, raw: Any) -> Optional[Dict[str, Any]]:
    """Validate one record from the shared database.

    Returns None for records with no real title or a source that is out of scope.
    Old app versions uploaded placeholder titles with a blob of links as the source;
    those stay in the database but are not shown. Only known fields survive, which
    also strips the presence data stored on one record.
    """
    if not isinstance(raw, dict):
        return None
    title = raw.get("title")
    if not isinstance(title, str) or is_generic_title(title):
        return None
    source = raw.get("source_url")
    source = source.strip() if isinstance(source, str) else ""
    if not links.is_allowed_source_url(source):
        return None

    record: Dict[str, Any] = {"slug": slug, "title": title.strip()[:_MAX_TITLE_LENGTH]}
    for field in _TEXT_FIELDS:
        value = raw.get(field)
        record[field] = value if isinstance(value, str) else ""
    record["source_url"] = source
    for field in _NUMBER_FIELDS:
        record[field] = _number(raw.get(field))
    image = raw.get("image_url")
    record["image_url"] = image if isinstance(image, str) and links.is_safe_image_url(image) else ""
    return record


def _identity_keys(record: Dict[str, Any]) -> Set[str]:
    keys = set()
    slug = record.get("slug")
    if slug:
        keys.add(f"slug:{slug}")
    source = record.get("source_url") or ""
    if links.is_fitgirl_page_url(source):
        keys.add(f"page:{_page_slug(source)}")
    elif source:
        keys.add(f"source:{source.rstrip('/')}")
    title = record.get("title") or ""
    if not is_generic_title(title):
        normalized = normalize_title(title)
        if normalized:
            keys.add(f"title:{normalized}")
    return keys


def dedupe_feed(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hide repeat uploads of the same game, keeping the newest. Display only.

    Nothing here may ever cause a delete: two records only merge when they share a
    slug, a FitGirl page, or a complete normalized title.
    """
    ordered = sorted(records, key=lambda record: record.get("timestamp_utc", ""), reverse=True)
    kept: List[Dict[str, Any]] = []
    owner_by_key: Dict[str, Dict[str, Any]] = {}
    for record in ordered:
        keys = _identity_keys(record)
        owner = next((owner_by_key[key] for key in keys if key in owner_by_key), None)
        if owner is not None:
            owner["used_count"] = max(owner.get("used_count", 0), record.get("used_count", 0))
            continue
        kept.append(record)
        for key in keys:
            owner_by_key[key] = record
    return sorted(kept, key=lambda record: record.get("timestamp_utc", ""), reverse=True)


def _query_keys(query: str) -> Set[str]:
    if "://" in query:
        if links.is_fitgirl_page_url(query):
            return {f"page:{_page_slug(query)}", f"slug:{_page_slug(query)}"}
        return {f"source:{query.rstrip('/')}"}
    keys = {f"slug:{sanitize_slug(query)}"}
    if not is_generic_title(query):
        normalized = normalize_title(query)
        if normalized:
            keys.add(f"title:{normalized}")
    return keys


def find_match(query: str, records: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the record for exactly this game from a URL, slug or title."""
    clean = (query or "").strip()
    if not clean:
        return None
    wanted = _query_keys(clean)
    for record in records:
        if wanted & _identity_keys(record):
            return record
    return None
