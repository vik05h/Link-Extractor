"""Local stand-in for the Firebase Realtime Database REST API.

It speaks real HTTP on localhost so the code under test runs unchanged, and it
never contacts the live database. It models only what the app relies on:
GET with shallow, PUT, PATCH, DELETE, server-side increments, and the admin-only
.settings path. Access rules are not modelled here; tests inject them with
`deny`. The real rules live in firebase/database.rules.json.
"""

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional


class FakeFirebase:
    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}
        self.admin_key = "correct-admin-key"
        self.requests: List[Dict[str, Any]] = []
        self.deny: Optional[Callable[[str, str, Optional[str]], bool]] = None
        self._lock = threading.Lock()
        self._server: Optional[ThreadingHTTPServer] = None

    @property
    def url(self) -> str:
        assert self._server is not None
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def start(self) -> None:
        fake = self

        class Handler(_Handler):
            server_state = fake

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def seed(self, path: str, value: Any) -> None:
        with self._lock:
            self._write(_segments(path), value)

    def read(self, path: str) -> Any:
        with self._lock:
            return self._read(_segments(path))

    def writes(self) -> List[Dict[str, Any]]:
        return [r for r in self.requests if r["method"] != "GET"]

    def _read(self, segments: List[str]) -> Any:
        node: Any = self.data
        for segment in segments:
            if not isinstance(node, dict) or segment not in node:
                return None
            node = node[segment]
        return node

    def _write(self, segments: List[str], value: Any) -> None:
        value = _prune(value)
        if not segments:
            self.data = value if isinstance(value, dict) else {}
            return
        node = self.data
        for segment in segments[:-1]:
            node = node.setdefault(segment, {})
        if value is None:
            node.pop(segments[-1], None)
            self._drop_empty_parents(segments[:-1])
        else:
            node[segments[-1]] = value

    def _drop_empty_parents(self, segments: List[str]) -> None:
        for depth in range(len(segments), 0, -1):
            parent = self._read(segments[: depth - 1])
            if isinstance(parent, dict) and parent.get(segments[depth - 1]) == {}:
                parent.pop(segments[depth - 1])

    def _resolve(self, segments: List[str], value: Any) -> Any:
        if isinstance(value, dict) and set(value) == {".sv"}:
            current = self._read(segments)
            base = current if isinstance(current, (int, float)) else 0
            return base + value[".sv"]["increment"]
        return value


class _Handler(BaseHTTPRequestHandler):
    server_state: FakeFirebase
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _reply(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method: str) -> None:
        state = self.server_state
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        auth = query.get("auth", [None])[0]
        path = urllib.parse.unquote(parsed.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        body = json.loads(raw.decode("utf-8")) if raw else None

        state.requests.append({"method": method, "path": path, "auth": auth, "body": body, "query": query})

        if not path.endswith(".json"):
            self._reply(400, {"error": "Missing .json suffix"})
            return
        clean = path[: -len(".json")].strip("/")

        if clean == ".settings/rules":
            if auth == state.admin_key:
                self._reply(200, {"rules": {}})
            else:
                self._reply(401, {"error": "Permission denied"})
            return

        if state.deny and state.deny(method, clean, auth):
            self._reply(401, {"error": "Permission denied"})
            return

        segments = _segments(clean)
        with state._lock:
            if method == "GET":
                value = state._read(segments)
                if query.get("shallow", ["false"])[0] == "true" and isinstance(value, dict):
                    value = {key: True for key in value}
                self._reply(200, value)
            elif method == "PUT":
                resolved = state._resolve(segments, body)
                state._write(segments, resolved)
                self._reply(200, resolved)
            elif method == "PATCH":
                resolved = {}
                for key, value in (body or {}).items():
                    child = segments + [key]
                    resolved[key] = state._resolve(child, value)
                    state._write(child, resolved[key])
                self._reply(200, resolved)
            elif method == "DELETE":
                state._write(segments, None)
                self._reply(200, None)
            else:
                self._reply(405, {"error": "Method not allowed"})

    def do_GET(self) -> None:
        self._handle("GET")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_PATCH(self) -> None:
        self._handle("PATCH")

    def do_DELETE(self) -> None:
        self._handle("DELETE")


def _segments(path: str) -> List[str]:
    return [segment for segment in path.strip("/").split("/") if segment]


def _prune(value: Any) -> Any:
    """Firebase never stores nulls or empty objects."""
    if isinstance(value, dict):
        cleaned = {key: _prune(item) for key, item in value.items()}
        cleaned = {key: item for key, item in cleaned.items() if item is not None}
        return cleaned or None
    return value
