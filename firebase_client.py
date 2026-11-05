"""Zero-SDK client for the Firebase Realtime Database REST API.

This is the one place that talks to the database. Failures raise FirebaseError,
so callers can tell "no data" apart from "the request failed". Access control
lives in firebase/database.rules.json on the server.
"""

import http.client
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping, Optional

import utils
from version import APP_VERSION

DEFAULT_DATABASE_URL = "https://link-extractor-8cbca-default-rtdb.asia-southeast1.firebasedatabase.app"

log = logging.getLogger(__name__)

_SAFE_KEY = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class FirebaseError(Exception):
    """A request that did not succeed. status is None when the server could not be reached."""

    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status

    @property
    def unreachable(self) -> bool:
        return self.status is None

    @property
    def denied(self) -> bool:
        return self.status in (401, 403)


def database_url() -> str:
    """The configured database, without a trailing slash."""
    return str(utils.load_settings().get("community_firebase_url") or DEFAULT_DATABASE_URL).rstrip("/")


def safe_key(key: Any) -> Optional[str]:
    """Return the key if it is safe to use as one database path segment, otherwise None."""
    return key if isinstance(key, str) and _SAFE_KEY.match(key) else None


def request(
    path: str,
    method: str = "GET",
    data: Any = None,
    *,
    auth: Optional[str] = None,
    query: Optional[Mapping[str, str]] = None,
    timeout: float = 6.0,
) -> Any:
    """Send one request and return the decoded JSON body. Raises FirebaseError on any failure."""
    params = dict(query or {})
    if auth:
        params["auth"] = auth
    url = f"{database_url()}/{urllib.parse.quote(path.strip('/'), safe='/.-_')}.json"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    headers = {"User-Agent": f"FitGirlLinkExtractor/{APP_VERSION}", "Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    # Error messages name the path only. The URL can contain the admin key.
    where = f"{method} /{path.strip('/')}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise FirebaseError(f"{where} was refused (HTTP {error.code})", error.code) from None
    except (OSError, ValueError, http.client.HTTPException) as error:
        raise FirebaseError(f"{where} could not reach the database ({type(error).__name__})") from None

    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except ValueError:
        raise FirebaseError(f"{where} returned invalid JSON") from None
