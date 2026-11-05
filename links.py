"""Which links this app trusts, decided by exact hostname and never by substring.

Links arrive from a shared database, the clipboard and web pages, and people run
what they download, so every check here works on the parsed hostname.
"""

import ipaddress
import re
import urllib.parse
from typing import List

FITGIRL_SITE_HOSTS = {"fitgirl-repacks.site", "www.fitgirl-repacks.site"}
FITGIRL_PASTE_HOSTS = {"paste.fitgirl-repacks.site"}
HOSTER_PAGE_HOSTS = {"fuckingfast.co", "www.fuckingfast.co"}
DIRECT_LINK_HOSTS = {"dl.fuckingfast.co"}

_PRIVATE_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}
_UNSAFE_URL_CHARS = re.compile(r"[\s\\\x00-\x1f\x7f]")
_URL_START = re.compile(r"https?://", re.IGNORECASE)
_SAFE_PACKAGE_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


def _parse(url: str):
    """Parse a URL, or return None if it is malformed or contains characters no real link has."""
    if not isinstance(url, str) or not url or _UNSAFE_URL_CHARS.search(url):
        return None
    try:
        parsed = urllib.parse.urlparse(url)
        # Accessing hostname and port raises on malformed authorities.
        _ = parsed.hostname, parsed.port
    except ValueError:
        return None
    return parsed


def hostname_of(url: str) -> str:
    """The lowercase hostname of a URL, or an empty string if there is none."""
    parsed = _parse(url)
    return (parsed.hostname or "").lower() if parsed else ""


def _has_host_in(url: str, hosts: set, *, schemes=("http", "https")) -> bool:
    parsed = _parse(url)
    if not parsed or parsed.scheme not in schemes or parsed.username or parsed.password:
        return False
    return (parsed.hostname or "").lower() in hosts


def _has_path(url: str) -> bool:
    return bool(urllib.parse.urlparse(url).path.strip("/"))


def is_direct_link(url: str) -> bool:
    """A finished download link on the hoster's download server. These are shared between users."""
    return _has_host_in(url, DIRECT_LINK_HOSTS, schemes=("https",)) and _has_path(url)


def is_hoster_page_url(url: str) -> bool:
    """A hoster page for one part, which still has to be resolved to a direct link."""
    return _has_host_in(url, HOSTER_PAGE_HOSTS) and _has_path(url)


def is_fitgirl_page_url(url: str) -> bool:
    """A game page on the real FitGirl site. The bare homepage does not count."""
    return _has_host_in(url, FITGIRL_SITE_HOSTS) and _has_path(url)


def is_fitgirl_paste_url(url: str) -> bool:
    """A link on the real FitGirl pastebin."""
    return _has_host_in(url, FITGIRL_PASTE_HOSTS)


def is_allowed_source_url(url: str) -> bool:
    """A source link that is safe to show as clickable. Empty means the record has no source."""
    if url == "":
        return True
    return _has_host_in(url, FITGIRL_SITE_HOSTS | FITGIRL_PASTE_HOSTS | HOSTER_PAGE_HOSTS)


def is_public_http_url(url: str) -> bool:
    """An http(s) URL that does not point at this machine or a private network."""
    parsed = _parse(url)
    if not parsed or parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in _PRIVATE_HOSTNAMES or host.endswith(".localhost"):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return address.is_global


def is_safe_image_url(url: str) -> bool:
    """A cover image link: a public web address or the app's own generated SVG banner."""
    if not isinstance(url, str) or not url:
        return False
    if url.startswith("data:image/svg+xml"):
        return True
    return is_public_http_url(url)


def extract_urls(text: str) -> List[str]:
    """All http(s) URLs in free text, including ones glued together when newlines were stripped."""
    urls = []
    starts = [match.start() for match in _URL_START.finditer(text or "")]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        candidate = re.split(r"[\s,]", text[start:end], maxsplit=1)[0]
        if candidate:
            urls.append(candidate)
    return urls


def part_name(url: str) -> str:
    """The display name of one part: its #filename, or else the last part of its path."""
    if "#" in url:
        return url.split("#")[-1]
    return url.rstrip("/").split("/")[-1]


def with_filename_fragments(urls: List[str], package_name: str) -> List[str]:
    """Give every URL a #filename so JDownloader 2 skips its Deep Link Analysis prompt."""
    safe_name = _SAFE_PACKAGE_CHARS.sub("_", package_name or "").strip("_") or "FitGirl_Repack"
    named = []
    for index, url in enumerate(urls):
        clean = url.strip()
        if not clean:
            continue
        named.append(clean if "#" in clean else f"{clean}#{safe_name}.part{index + 1:03d}.rar")
    return named
